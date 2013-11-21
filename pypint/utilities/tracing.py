# coding=utf-8
"""
Summary
-------
Collection of utility functions related to the callstack and traceback.

.. moduleauthor:: Torbjörn Klatt <t.klatt@fz-juelich.de>
"""

import inspect


def func_name(obj=None):
    """
    Summary
    -------
    Formats the calling functions name.

    Extended Summary
    ----------------
    Formats the calling functions name in the format
    ``'ClassName.FunctionName(): '``.

    Parameters
    ----------
    obj : object
        Instance of an object the calling function is a member of.

    Returns
    -------
    formatted function name : str
        Formatted function name of calling function.

    Examples
    --------
    >>> from pypint.utilities import func_name
    >>> class MyClass(object):
    ...     def my_func(self):
    ...         print(func_name(self) + "Hello World!")
    >>> my_obj = MyClass()
    >>> my_obj.my_func()
    MyClass.my_func(): Hello World!
    """
    return "{:s}.{:s}(): "\
           .format(obj.__class__.__name__, inspect.stack()[1][3])
