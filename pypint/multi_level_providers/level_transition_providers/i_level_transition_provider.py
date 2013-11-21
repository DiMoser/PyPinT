# coding=utf-8
"""

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

import numpy as np
from pypint.utilities import func_name


class ILevelTransitionProvider(object):
    """
    Summary
    -------
    Interface for level transition providers.
    """
    def __init__(self, num_fine_points=-1, num_coarse_points=-1):
        """
        Parameters
        ----------
        num_fine_points : integer
            Number of points of the fine level.
        num_coarse_points : integer
            Number of points of the coarse level.
        """
        self._prolongation_operator = None
        self._restringation_operator = None
        self._n_fine_points = int(num_fine_points)
        self._n_coarse_points = int(num_coarse_points)

    def prolongate(self, coarse_data):
        """
        Summary
        -------
        Prolongates given data from the coarse to the fine level.

        Parameters
        ----------
        coarse_data : numpy.ndarray
            Coarse data vector to prolongate.

        Returns
        -------
        prolongated data : numpy.ndarray
            Prolongated data on the fine level.

        Raises
        ------
        ValueError
            * if ``coarse_data`` is not a ``numpy.ndarray``
            * if ``coarse_data`` has more or less entries than :py:attr:`.num_coarse_points`
        """
        if not isinstance(coarse_data, np.ndarray):
            raise ValueError(func_name(self) +
                             "Given coarse data is not a numpy.ndarray: {:s}"
                             .format(type(coarse_data)))
        if coarse_data.size != self.num_coarse_points:
            raise ValueError(func_name(self) +
                             "Given coarse data is of wrong size: {:d}"
                             .format(coarse_data.size))

    def restringate(self, fine_data):
        """
        Summary
        -------
        Restringates given data from the fine to the coarse level.

        Parameters
        ----------
        fine_data : numpy.ndarray
            Fine data vector to restringate.

        Returns
        -------
        restringated data : numpy.ndarray
            Restringated data on the coarse level.

        Raises
        ------
        ValueError
            * if ``fine_data`` is not a ``numpy.ndarray``
            * if ``fine_data`` has more or less entries than :py:attr:`.num_fine_points`
        """
        if not isinstance(fine_data, np.ndarray):
            raise ValueError(func_name(self) +
                             "Given fine data is not a numpy.ndarray: {:s}"
                             .format(type(fine_data)))
        if fine_data.size != self.num_fine_points:
            raise ValueError(func_name(self) +
                             "Given fine data is of wrong size: {:d}"
                             .format(fine_data.size))

    @property
    def prolongation_operator(self):
        """
        Summary
        -------
        Accessor for the prolongation operator.

        Parameters
        ----------
        prolongation_operator : numpy.ndarray
            New prolongation operator to be used.

        Returns
        -------
        prolongation operator : numpy.ndarray
            Current prolongation operator.
        """
        return self._prolongation_operator

    @prolongation_operator.setter
    def prolongation_operator(self, prolongation_operator):
        self._prolongation_operator = prolongation_operator

    @property
    def restringation_operator(self):
        """
        Summary
        -------
        Accessor for the restringation operator.

        Parameters
        ----------
        restringation_operator : numpy.ndarray
            New restringation operator to be used.

        Returns
        -------
        restringation operator : numpy.ndarray
            Current restringation operator.
        """
        return self._restringation_operator

    @restringation_operator.setter
    def restringation_operator(self, restringation_operator):
        self._restringation_operator = restringation_operator

    @property
    def num_fine_points(self):
        """
        Summary
        -------
        Accessor for the number of points of the fine level.

        Returns
        -------
        number of fine points : integer
            Number of points on the fine level.
        """
        return self._n_fine_points

    @property
    def num_coarse_points(self):
        """
        Summary
        -------
        Accessor for the number of points of the coarse level.

        Extended Summary
        ----------------
        The number of coarse points equals :math:`\frac{n_{fine}+1}{2}`.

        Returns
        -------
        number of coarse points : integer
            Number of points on the fine level.
        """
        return self._n_coarse_points
