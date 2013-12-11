# coding=utf-8
"""

.. moduleauthor: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

from copy import deepcopy
import numpy as np
from pypint import LOG


class IWeightFunction(object):
    """
    Summary
    -------
    Provider for integration weights functions.

    Extended Summary
    ----------------
    This is an abstract interface for providers of integration weights
    functions.
    """
    def __init__(self):
        self._weights = None

    def init(self, *args, **kwargs):
        """
        Summary
        -------
        Sets and defines the weights function.

        Parameters
        ----------
        args, kwargs
            Implementation defined type to specify the weight function's
            parameters.

        Notes
        -----
        The implementation and behaviour must and will be defined by
        specializations of this interface.
        Implementations are allowed to add further named arguments.
        """
        pass

    def evaluate(self, nodes, interval=None):
        """
        Summary
        -------
        Computes weights for given nodes based on set weight function.

        Extended Summary
        ----------------

        Parameters
        ----------
        nodes : numpy.ndarray
            Array of nodes to compute weights for.
        interval : numpy.ndarray
            Array with the interval boundaries.
            If ``None`` the boundaries of the given nodes are used.
        Returns
        -------
        computed weights : numpy.ndarray
            Vector of computed weights.

        Notes
        -----
        The implementation and behaviour must and will be defined by
        specializations of this interface.
        """
        if interval is None:
            self._interval = np.array([nodes[0], nodes[-1]])
        else:
            self._interval = interval

    @property
    def weights(self):
        """
        Summary
        -------
        Accessor for cached computed weights.

        Returns
        -------
        computed weights : numpy.ndarray
            Cached computed weights.
        """
        return self._weights

    def __copy__(self):
        copy = self.__class__.__new__(self.__class__)
        copy.__dict__.update(self.__dict__)
        return copy

    def __deepcopy__(self, memo):
        copy = self.__class__.__new__(self.__class__)
        memo[id(self)] = copy
        for item, value in self.__dict__.items():
            setattr(copy, item, deepcopy(value, memo))
        return copy
