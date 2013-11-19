# coding=utf-8
"""
Logging Framework for PyPinT

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

import logging
import logging.config


STD_LOGGERS = {}
"""
Summary
-------
Dictionary of standard Logger configurations.
"""


class Logging(object):
    """
    Summary
    -------
    Logging framework providing easy access to a Python build-in
    ``logging.Logger``.

    Examples
    --------
    >>> from pypint import LOG
    >>> LOG.debug("My debug message.")
    """

    _logger = logging.getLogger()
    """
    """

    @staticmethod
    def init(name="ConsoleLogger", options=None):
        """
        Summary
        -------
        Initializes and configures the logger.

        Parameters
        ----------
        name : str
            Name of the logger to configure.
            If ``None`` or an empty string is given, the logger is not changed.
        options : dict
            Optional dictionary of logger options.
            If ``None`` is given or ``dict`` is not a dictionary,
            :py:data:`.STD_LOGGERS` is used.
        """
        if options is not None \
                and isinstance(options, dict):
            logging.config.dictConfig(options)
        else:
            logging.config.dictConfig(STD_LOGGERS)
        if name is not None or name != "":
            Logging._logger = logging.getLogger(name)

    @staticmethod
    def logger():
        """
        Summary
        -------
        Accessor for the currently configured logger.

        Returns
        -------
        current logger : :py:class:`logging.Logger`
            Currently configured logger instance.

        See Also
        --------
        .Logging._logger
            returned private class variable
        """
        return Logging._logger


STD_LOGGERS = {
    "version": 1,
    "formatters": {
        "simple": {
            "format": '%(levelname)s %(module)s.%(funcName)s: %(message)s',
            "datefmt": '%d.%m.%y %H:%M:%S %Z'
        },
        "precise": {
            "format": '%(asctime)s - %(levelname)s - %(module)s.%(filename)s.%(funcname)s:%(lineno)d - %(message)s'
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "precise",
            "filename": "logger.log",
            "maxBytes": 1024,
            "backupCount": 3
        }
    },
    "loggers": {
        "ConsoleLogger": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": "no"
        },
        "LogfileLogger": {
            "level": "INFO",
            "handlers": ["file"]
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"]
    }
}
