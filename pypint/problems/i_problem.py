# coding=utf-8
"""

.. moduleauthor: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""


class IProblem(object):
    def __init__(self):
        self._function = None
        self._time_start = None
        self._time_end = None

    def eval(self, time, phi_of_time):
        pass

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, function):
        self._function = function

    @property
    def time_start(self):
        return self._time_start

    @time_start.setter
    def time_start(self, time_start):
        self._time_start = time_start

    @property
    def time_end(self):
        return self._time_end

    @time_end.setter
    def time_end(self, time_end):
        self._time_end = time_end
