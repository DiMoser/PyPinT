# coding=utf-8
"""

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

from .i_plotter import IPlotter
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import is_interactive
from pypint.plugins.plotters.__init__ import colorline
from pypint.utilities import func_name
from pypint import LOG


class SingleSolutionPlotter(IPlotter):
    """
    Summary
    -------
    Plotter for a single solution of an iterative time solver.

    See Also
    --------
    .IPlotter
        overridden class
    """
    def __init__(self, *args, **kwargs):
        super(SingleSolutionPlotter, self).__init__(args, **kwargs)
        self._solver = None
        self._solution = None
        self._nodes = None
        self._errplot = False

    def plot(self, *args, **kwargs):
        """
        Summary
        -------
        Plots the solution and optional also the error for each iteration.

        Parameters
        ----------
        solver : IIterativeTimeSolver
            The solver instance used to calculate the solution.

        solution : ISolution
            The solution.

        errplot : boolean
            (optional)
            If given and ``True`` also plots the errors for each iteration found in the solution.

        residualplot : boolean
            (optional)
            If given and ``True`` also plots the residual for each iteration found in the solution.
        """
        super(SingleSolutionPlotter, self).plot(args, **kwargs)
        if "solver" not in kwargs or "solution" not in kwargs:
            raise ValueError(func_name(self) +
                             "Both, solver and solution, must be given.")

        self._solver = kwargs["solver"]
        self._solution = kwargs["solution"]
        self._nodes = self._solution.points
        _subplots = 1
        _curr_subplot = 0
        if "errorplot" in kwargs and kwargs["errorplot"]:
            _subplots += 1
            self._errplot = True
        if "residualplot" in kwargs and kwargs["residualplot"]:
            _subplots += 1
            self._residualplot = True

        if self._solver.problem.time_start != self._nodes[0]:
            self._nodes = np.concatenate(([self._solver.problem.time_start], self._nodes))
        if self._solver.problem.time_end != self._nodes[-1]:
            self._nodes = np.concatenate((self._nodes, [self._solver.problem.time_end]))

        if self._errplot or self._residualplot:
            plt.suptitle(r"after {:d} iterations; overall reduction: {:.2e}"
                         .format(self._solution.used_iterations, self._solution.reductions["solution"][-1]))
            _curr_subplot += 1
            plt.subplot(_subplots, 1, _curr_subplot)

        self._final_solution()
        plt.title(self._solver.problem.__str__())

        if self._errplot:
            _curr_subplot += 1
            plt.subplot(3, 1, _curr_subplot)
            self._error_plot()

        if self._residualplot:
            _curr_subplot += 1
            plt.subplot(3, 1, _curr_subplot)
            self._residual_plot()

        if self._file_name is not None:
            fig = plt.gcf()
            fig.set_dpi(300)
            fig.set_size_inches((15., 15.))
            LOG.debug("Plotting figure with size (w,h) {:s} inches and {:d} DPI."
                      .format(fig.get_size_inches(), fig.get_dpi()))
            fig.savefig(self._file_name)

        if is_interactive():
            plt.show(block=True)
        else:
            plt.close('all')

    def _final_solution(self):
        if self._solution.solution().dtype == np.complex:
            colorline(self._solution.solution().real, self._solution.solution().imag)
        else:
            plt.plot(self._nodes, self._solution.solution(), label="Solution")
        if self._solver.problem.has_exact() and self._solution.errors[-1].max() > 1e-2:
            exact = self._solution.exact()
            if exact.dtype == np.complex:
                colorline(exact.real, exact.imag)
            else:
                plt.plot(self._nodes, exact, label="Exact")
        if self._solution.solution().dtype == np.complex:
            plt.xlabel("real")
            plt.ylabel("imag")
        else:
            plt.xticks(self._nodes)
            plt.xlabel("integration nodes")
            plt.ylabel(r'$u(t, \phi_t)$')
            plt.xlim(self._nodes[0], self._nodes[-1])
            plt.legend()
        plt.grid(True)

    def _error_plot(self):
        errors = self._solution.errors
        for i in range(0, errors.size):
            plt.plot(self._nodes, errors[i], label=r"Iteraion {:d}".format(i+1))
        plt.xticks(self._nodes)
        plt.xlim(self._nodes[0], self._nodes[-1])
        plt.yscale("log")
        plt.xlabel("integration nodes")
        plt.ylabel(r'absolute error of iterations')
        #plt.legend(loc="upper center", fontsize="x-small")
        plt.grid(True)

    def _residual_plot(self):
        _residuals = self._solution.residuals
        # if np.flatnonzero(_residuals).size > 0:
        for i in range(0, _residuals.size):
            plt.plot(self._nodes, _residuals[i], label=r"Iteration {:d}".format(i+1))
        plt.xticks(self._nodes)
        plt.xlim(self._nodes[0], self._nodes[-1])
        plt.yscale("log")
        plt.xlabel("integration nodes")
        plt.ylabel(r'residual')
        #plt.legend(loc="upper center", fontsize="x-small")
        plt.grid(True)
        # else:
        #     LOG.info("All residual values are exact zero. Not plotting residuals.")
