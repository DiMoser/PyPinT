# coding=utf-8
"""

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

import matplotlib.pyplot as plt
from pypint import LOG


class IPlotter(object):
    """
    Summary
    -------
    Basic interface for plotters.

    Parameters
    ----------
    file_name : string
        (optional)
        File name to store the plot to.
    """
    def __init__(self, *args, **kwargs):
        if "file_name" in kwargs and \
                isinstance(kwargs["file_name"], str) and len(kwargs["file_name"]) > 0:
            self._file_name = kwargs["file_name"]
            LOG.debug("Non-interactive plotting. Saving to '{:s}'".format(self._file_name))
            plt.ioff()
        else:
            self._file_name = None
            LOG.debug("Interactive plotting.")
            plt.ion()

    def plot(self, *args, **kwargs):
        """
        Summary
        -------
        Executing the plotter implementation.
        """
        pass
