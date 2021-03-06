# coding=utf-8
"""*PyPinT* is a framework for Parallel-in-Time integration routines.

The main purpose of *PyPinT* is to provide a framework for educational use and prototyping new parallel-in-time
algorithms.
As well it will aid in developing a high-performance C++ implementation for massively parallel computers providing the
benefits of parallel-in-time routines to a zoo of time integrators in various applications.

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
.. moduleauthor:: Dieter Moser <d.moser@fz-juelich.de>
"""

from sys import version_info
if version_info.major < 3 and version_info.minor < 3:
    raise RuntimeError("PyPinT requires at least Python 3.3.")

try:
    from pypint.version import git_revision as __git_revision__
    from pypint.version import version as __version__
except ImportError:
    import warnings
    warnings.warn("Version file could not be loaded!")
    __git_revision__ = "UNKNOWN"
    __version__ = "UNKNOWN"
