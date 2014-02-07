# coding=utf-8
"""
.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""
from copy import deepcopy
import warnings as warnings

import numpy as np

from pypint.solvers.i_iterative_time_solver import IIterativeTimeSolver
from pypint.integrators.sdc_integrator import SdcIntegrator
from pypint.integrators.node_providers.gauss_lobatto_nodes import GaussLobattoNodes
from pypint.integrators.weight_function_providers.polynomial_weight_function import PolynomialWeightFunction
from pypint.problems import IInitialValueProblem, problem_has_exact_solution
from pypint.solvers.states.sdc_solver_state import SdcSolverState
from pypint.solvers.diagnosis.norms import supremum_norm
from pypint.plugins.timers.timer_base import TimerBase
from pypint.utilities.threshold_check import ThresholdCheck
from pypint.utilities import assert_is_instance, assert_condition, func_name
from pypint import LOG

# General Notes on Implementation
# ===============================
#
# Names and Meaning of Indices
# ----------------------------
# T_max (num_time_steps) | number of time steps
# N     (num_nodes)      | number of integration nodes per time step
# t                      | index of current time step; interval: [0, T_max)
# n                      | index of current node of current time step; interval: [1, N)
#                        |  the current node is always the next node, i.e. the node we are
#                        |  calculating the value for
# i                      | index of current point in continuous array of points


class Sdc(IIterativeTimeSolver):
    """
    Summary
    -------
    *Spectral Deferred Corrections* method for solving first order ODEs.

    Extended Summary
    ----------------
    The *Spectral Deferred Corrections* (SDC) method is described in [Minion2003]_ (Equation 2.7)

    Default Values:

        * :py:attr:`.ThresholdCheck.max_iterations`: 5

        * :py:attr:`.ThresholdCheck.min_reduction`: 1e-7

        * :py:attr:`.num_time_steps`: 1

        * :py:attr:`.num_nodes`: 3

    Given the total number of time steps :math:`T_{max}`, number of integration nodes per time
    step :math:`N`, current time step :math:`t \\in [0,T_{max})` and the next integration node
    to consider :math:`n \\in [0, N)`.
    Let :math:`[a,b]` be the total time interval to integrate over.
    For :math:`T_{max}=3` and :math:`N=4`, this can be visualized as::

           a                                            b
           |                                            |
           |    .    .    |    .    .    |    .    .    |
        t  0    0    0    0    1    1    1    2    2    2
        n  0    1    2    3    1    2    3    1    2    3
        i  0    1    2    3    4    5    6    7    8    9

    In general, the value at :math:`a` (i.e. :math:`t=n=i=0`) is the initial value.

    See Also
    --------
    .IIterativeTimeSolver :
        implemented interface

    Examples
    --------
    >>> from pypint.solvers.sdc import Sdc
    >>> from examples.problems.constant import Constant
    >>> # setup the problem
    >>> my_problem = Constant(constant=-1.0)
    >>> # create the solver
    >>> my_solver = Sdc()
    >>> # initialize the solver with the problem
    >>> my_solver.init(problem=my_problem, num_time_steps=1, num_nodes=3)
    >>> # run the solver and get the solution
    >>> my_solution = my_solver.run()
    >>> # print the solution of the last iteration
    >>> print(my_solution.solution(-1))
    [  1.00000000e+00   5.00000000e-01  -1.11022302e-16]
    """
    def __init__(self, **kwargs):
        super(Sdc, self).__init__(**kwargs)
        self._num_time_steps = 1
        self.threshold = ThresholdCheck(min_threshold=1e-7, max_threshold=10,
                                              conditions=("residual", "iterations"))
        self.__exact = np.zeros(0)
        self._state = None
        self.__time_points = {
            'steps': np.zeros(0),
            'nodes': np.zeros(0)
        }
        self._deltas = {
            't': 0.0,
            'n': np.zeros(0)
        }
        self.timer = TimerBase()

    def init(self, problem, integrator=SdcIntegrator(), **kwargs):
        """
        Summary
        -------
        Initializes SDC solver with given problem and integrator.

        Parameters
        ----------
        num_time_steps : :py:class:`int`
            Number of time steps to be used within the time interval of the problem.

        nodes_type : :py:class:`.INodes`
            Type of integration nodes to be used.

        weights_type : :py:class:`.IWeightFunction`
            Integration weights function to be used.

        type : :py:class:`str`
            Specifying the type of the SDC steps being implicit (``impl``), explicit (``expl``) or semi-implicit
            (``semi``).
            Default is ``expl``.

        Raises
        ------
        ValueError :
            If given problem is not an :py:class:`.IInitialValueProblem`.

        See Also
        --------
        .IIterativeTimeSolver.init
            overridden method
        """
        assert_is_instance(problem, IInitialValueProblem,
                           "SDC requires an initial value problem: {:s}".format(problem.__class__.__name__),
                           self)

        super(Sdc, self).init(problem, integrator, **kwargs)

        if 'num_time_steps' in kwargs:
            self._num_time_steps = kwargs['num_time_steps']

        if 'num_nodes' in kwargs:
            _num_nodes = kwargs['num_nodes']
        elif 'nodes_type' in kwargs and kwargs['nodes_type'].num_nodes is not None:
            _num_nodes = kwargs['nodes_type'].num_nodes
        elif integrator.nodes_type.num_nodes is not None:
            _num_nodes = integrator.nodes_type.num_nodes
        else:
            raise ValueError(func_name(self) +
                             "Number of nodes per time step not given.")

        if 'nodes_type' not in kwargs:
            kwargs['nodes_type'] = GaussLobattoNodes()

        if 'weights_type' not in kwargs:
            kwargs['weights_type'] = PolynomialWeightFunction()

        # initialize solver state
        self._state = SdcSolverState(num_nodes=_num_nodes, num_time_steps=self.num_time_steps)

        # TODO: do we need this?
        _num_points = self.num_time_steps * (_num_nodes - 1) + 1

        self.__exact = np.zeros(_num_points, dtype=self.problem.numeric_type)

        # compute time step and node distances
        self.state.delta_interval = self.problem.time_end - self.problem.time_start
        self._deltas['t'] = self.state.delta_interval / self.num_time_steps  # width of a single time step (equidistant)
        #  start time points of time steps
        self.__time_points['steps'] = np.linspace(self.problem.time_start,
                                                  self.problem.time_end, self.num_time_steps + 1)

        # initialize and transform integrator for time step width
        self._integrator.init(kwargs['nodes_type'], _num_nodes, kwargs['weights_type'],
                              interval=np.array([self.__time_points['steps'][0], self.__time_points['steps'][1]],
                                                dtype=np.float))
        del _num_nodes  # number of nodes is now always queried from integrator
        self.__time_points['nodes'] = np.zeros(_num_points, dtype=np.float)
        self._deltas['n'] = np.zeros(self.num_time_steps * (self.num_nodes - 1) + 1)

        # copy the node provider so we do not alter the integrator's one
        _nodes = deepcopy(self._integrator.nodes_type)
        for _t in range(0, self.num_time_steps):
            # transform Nodes (copy) onto new time step for retrieving actual integration nodes
            _nodes.interval = \
                np.array([self.__time_points['steps'][_t], self.__time_points['steps'][_t + 1]])
            for _n in range(0, self.num_nodes - 1):
                _i = _t * (self.num_nodes - 1) + _n
                self.__time_points['nodes'][_i] = _nodes.nodes[_n]
                self._deltas['n'][_i + 1] = _nodes.nodes[_n + 1] - _nodes.nodes[_n]
        self.__time_points['nodes'][-1] = _nodes.nodes[-1]

    def run(self, core):
        """
        Summary
        -------
        Applies SDC solver to the initialized problem setup.

        Extended Summary
        ----------------
        Solves the given problem with the explicit SDC algorithm.

        The output for the iterations explained:

            :**iter**:
                The iteration number.

            :**rel red**:
                The relative reduction of the solution from one iteration to the previous.
                Is only displayed from the second iteration onwards.

            :**time**:
                Seconds taken for the iteration.

            :**resid**:
                Residual of the last time step of the iteration.

            :**err red**:
                Reduction of the absolute error from the first iteration to the current.
                Is only displayed from the second iteration onwards and only if the given problem
                provides a function of the exact solution (see :py:meth:`.problem_has_exact_solution()`).

        The output for the time steps of an iteration explained (will only show up when running with
        logger level ``DEBUG``):

            :**step**:
                Number of the time step.

            :**t_0**:
                Start of the time step interval.

            :**t_1**:
                End of the time step interval.

            :**resid**:
                Residual of the time step.

            :**err**:
                Inifnity norm of error for the time step.
                Is only displayed if the given problem provides a function for the
                exact solution (see :py:meth:`.problem_has_exact_solution()`).

        Parameters
        ----------

        Raises
        ------

        See Also
        --------
        .IIterativeTimeSolver.run
            overridden method
        """
        super(Sdc, self).run(core)

        # start logging output
        self._print_header()

        # initialize iteration timer of same type as global timer
        _iter_timer = self.timer.__class__()

        # start global timing
        self.timer.start()

        # start iterations
        self.__exact[0] = self.problem.initial_value
        _iter = 0
        while self.threshold.has_reached() is None:
            _iter += 1
            # initialize a new integration state
            self.state.new()
            # set the initial value
            self.state.current_step.solution.value = self.problem.initial_value
            self.state.current_step.solution.time_point = self.problem.time_start

            # step result table header
            if problem_has_exact_solution(self.problem, self):
                self._output(['node', 't_0', 't_1', 'resid', 'err'],
                             ['str', 'str', 'str', 'str', 'str'],
                             padding=10, debug=True)
            else:
                self._output(['node', 't_0', 't_1', 'resid'],
                             ['str', 'str', 'str', 'str'],
                             padding=10, debug=True)

            # iterate on time steps
            _iter_timer.start()
            for _current_time_step in self.state.current_iteration:
                # run this time step
                self._time_step()
                self.state.current_iteration.element_done()
            _iter_timer.stop()

            # log this iteration's summary
            if _iter == 1:
                # on first iteration we do not have comparison values
                self._output([_iter, None, _iter_timer.past()],
                             ['int', None, 'float'],
                             padding=4)
            else:
                if problem_has_exact_solution(self.problem, self) and _iter > 0:
                    # we could compute the correct error of our current solution
                    self._output([_iter, self.state.solution.solution_reduction[self.state.current_iteration_index],
                                  _iter_timer.past(), self.state.current_step.solution.residual,
                                  self.state.solution.error_reduction[self.state.current_iteration_index]],
                                 ['int', 'exp', 'float', 'exp', 'exp'],
                                 padding=4)
                else:
                    self._output([_iter, self.state.solution.solution_reduction[self.state.current_iteration_index],
                                  _iter_timer.past(), self.state.current_step.solution.residual],
                                 ['int', 'exp', 'float', 'exp'],
                                 padding=4)

            # check termination criteria
            self.threshold.check(self.state)

            # finalize this iteration (i.e. TrajectorySolutionData.finalize())
            self.state.current_iteration.done()

            # continue with next iteration if we are not yet finished
            if not self.threshold.has_reached():
                self.state.element_done()
        # end while:self._threshold_check.has_reached() is None
        self.timer.stop()

        # finalize the IterativeSolution
        self.state.done()

        if _iter <= self.threshold.max_iterations:
            LOG.info("> Converged after {:d} iteration(s).".format(_iter))
            LOG.info(">   {:s}".format(self.threshold.has_reached(human=True)))
            LOG.info(">   Solution Reduction: {:.3e}"
                     .format(self.state.solution.solution_reduction[self.state.current_iteration_index]))
            LOG.info(">   Final Residual: {:.3e}".format(supremum_norm(self.state[-1][-1][-1].solution.residual)))
            if problem_has_exact_solution(self.problem, self):
                LOG.info(">   Error Reduction: {:.3e}"
                         .format(self.state.solution.error_reduction[self.state.current_iteration_index]))
        else:
            warnings.warn("Explicit SDC: Did not converged: {:s}".format(self.problem))
            LOG.info("> FAILED: After maximum of {:d} iteration(s).".format(_iter))
            LOG.info(">   Solution Reduction: {:.3e}"
                     .format(self.state.solution.solution_reduction[self.state.current_iteration_index]))
            LOG.info(">         Final Residual: {:.3e}".format(supremum_norm(self.state[-1][-1][-1].solution.residual)))
            if problem_has_exact_solution(self.problem, self):
                LOG.info(">   Error Reduction: {:.3e}"
                         .format(self.state.solution.error_reduction[self.state.current_iteration_index]))
            LOG.warn("SDC Failed: Maximum number iterations reached without convergence.")

        self._print_footer()

        return self.state.solution

    @property
    def num_time_steps(self):
        """
        Summary
        -------
        Accessor for the number of time steps within the interval.

        Returns
        -------
        number time steps : integer
            Number of time steps within the problem-given time interval.
        """
        return self._num_time_steps

    @property
    def num_nodes(self):
        """
        Summary
        -------
        Accessor for the number of integration nodes per time step.

        Returns
        -------
        number of nodes : integer
            Number of integration nodes used within one time step.
        """
        return self._integrator.nodes_type.num_nodes

    def _time_step(self):
        # copy the solution of the previous time step's last node to the first node of this time step
        #  (they should be the same in most cases!)
        if self.state.current_time_step_index != 0:
            if self.state.current_iteration_index > 0:
                self.state.current_time_step[0].solution.value = \
                    self.state.current_iteration.previous_time_step[-1].solution.value.copy()
                self.state.current_time_step[0].solution.time_point = \
                    self.state.current_iteration.previous_time_step[-1].solution.time_point

        for _current_step in self.state.current_time_step:
            if self.state.current_step_index == 0:
                # always skip the first step of a time step.
                #  it is either the very initial one or the final step of the previous time step
                pass
            else:
                self._sdc_step()

            # finished a step; continuing with the next one
            self.state.current_time_step.element_done()

        # finalizing the current time step (i.e. TrajectorySolutionData.finalize)
        self.state.current_time_step.done()

    def _sdc_step(self):
        _current_time_step_index = self.state.current_time_step_index
        _current_step_index = self.state.current_step_index
        _current_point_global_index = _current_time_step_index * (self.num_nodes - 1) + _current_step_index
# self.core_state.calculate_node_range()

        # get current steps' time data
        self.state.current_step.delta_tau = self._deltas['n'][_current_step_index]
        self.state.current_step.solution.time_point = self.__time_points['nodes'][_current_point_global_index]
# self.core_state.curr_time_pnt = self.__time_points['nodes'][self.core_state.prev_pnt_ndx]
# self.core_state.next_time_pnt = self.__time_points['nodes'][self.core_state.curr_pnt_ndx]

        # copy solution of previous iteration to this one
        self.state.current_step.solution.value = \
            self.state.previous_iteration[_current_time_step_index][_current_step_index].solution.value.copy()

        # gather values for integration and evaluate problem at given points
        _integrate_values = \
            np.array(
                [
                    self.problem.evaluate(self.state.current_time_step[0].solution.time_point,
                                          self.state.current_time_step[0].solution.value.copy())
                ], dtype=self.problem.numeric_type
            )
        for _index in range(1, _current_step_index):
            _integrate_values = \
                np.append(_integrate_values,
                          np.array(
                              [
                                  self.problem.evaluate(self.state.current_time_step[_index].solution.time_point,
                                                        self.state.current_time_step[_index].solution.value.copy())
                              ], dtype=self.problem.numeric_type
                          ), axis=0)
        for _index in range(0, (self.num_nodes - _current_step_index)):
            _integrate_values = \
                np.append(_integrate_values,
                          np.array(
                              [
                                  self.problem.evaluate(self.state.previous_time_step[_index].solution.time_point,
                                                        self.state.previous_time_step[_index].solution.value.copy())
                              ], dtype=self.problem.numeric_type
                          ), axis=0)
        assert_condition(_integrate_values.size == len(self.state.current_time_step),
                         ValueError, "Number of integration values not correct: {:d} != {:d}"
                                     .format(_integrate_values.size, len(self.state.current_time_step)),
                         self)

        # integrate
        self.state.current_step.integral = self._integrator.evaluate(_integrate_values,
                                                                     last_node_index=_current_step_index)

        # compute step
        self._core.run(self.state)

        # calculate residual
        _original_integral = self.state.current_step.integral.copy()  # just a backup
        _integrate_values[_current_step_index] = \
            np.array(
                [
                    self.problem.evaluate(self.state.current_step.solution.time_point,
                                          self.state.current_step.solution.value.copy())
                ], dtype=self.problem.numeric_type
            )

        _residual_integral = 0
        for i in range(1, _current_step_index + 1):
            _residual_integral += self._integrator.evaluate(_integrate_values, last_node_index=i)
        del _integrate_values
        self.state.current_step.integral = _residual_integral.copy()
        del _residual_integral

        self._core.compute_residual(self.state)
        self.state.current_step.integral = _original_integral.copy()
        del _original_integral

        # calculate error
        self._core.compute_error(self.state, problem=self.problem)

        # log
        if problem_has_exact_solution(self.problem, self):
            self._output([self.state.current_step_index,
                          self.state.current_time_step.previous_step.time_point,
                          self.state.current_step.time_point,
                          supremum_norm(self.state.current_step.solution.residual),
                          supremum_norm(self.state.current_step.solution.error)],
                         ['int', 'float', 'float', 'exp', 'exp'],
                         padding=10, debug=True)
        else:
            self._output([self.state.current_step_index,
                          self.state.current_time_step.previous_step.time_point,
                          self.state.current_step.time_point,
                          supremum_norm(self.state.current_step.solution.residual)],
                         ['int', 'float', 'float', 'exp'],
                         padding=10, debug=True)

        # finalize this current step (i.e. StepSolutionData.finalize())
        self.state.current_step.done()

    def _print_header(self):
        LOG.info("> " + '#' * 78)
        LOG.info("{:#<80}".format("> START: {:s} SDC ".format(self._core.name)))
        LOG.info(">   Interval:               [{:.3f}, {:.3f}]".format(self.problem.time_start, self.problem.time_end))
        LOG.info(">   Time Steps:             {:d}".format(self.num_time_steps))
        LOG.info(">   Integration Nodes:      {:d}".format(self.num_nodes))
        LOG.info(">   Termination Conditions: {:s}".format(self.threshold.print_conditions()))
        LOG.info(">   Problem: {:s}".format(self.problem))
        LOG.info("> " + '-' * 78)

        # itartion result table header
        if problem_has_exact_solution(self.problem, self):
            self._output(['iter', 'rel red', 'time', 'resid', 'err red'],
                         ['str', 'str', 'str', 'str', 'str'],
                         padding=4)
        else:
            self._output(['iter', 'rel red', 'time', 'resid'],
                         ['str', 'str', 'str', 'str'],
                         padding=4)

    def _print_footer(self):
        LOG.info("{:#<80}".format("> FINISHED: {:s} SDC ({:.3f} sec) ".format(self._core.name, self.timer.past())))
        LOG.info("> " + '#' * 78)

    def _output(self, values, types, padding=0, debug=False):
        assert_condition(len(values) == len(types), ValueError, "Number of values must equal number of types.", self)
        _outstr = ' ' * padding
        for i in range(0, len(values)):
            if values[i] is None:
                _outstr += ' ' * 10
            else:
                if types[i] == 'float':
                    _outstr += "{: 10.3f}".format(values[i])
                elif types[i] == 'int':
                    _outstr += "{: 10d}".format(values[i])
                elif types[i] == 'exp':
                    _outstr += "{: 10.2e}".format(values[i])
                elif types[i] == 'str':
                    _outstr += "{: >10s}".format(values[i])
                else:
                    raise ValueError(func_name(self) +
                                     "Given type for value '{:s}' is invalid: {:s}"
                                     .format(values[i], types[i]))
            _outstr += "    "
        if debug:
            LOG.debug("!> {:s}".format(_outstr))
        else:
            LOG.info("> {:s}".format(_outstr))


__all__ = ['Sdc']
