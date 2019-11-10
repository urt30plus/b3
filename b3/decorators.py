import functools

__author__ = 'Courgette, Fenix'
__version__ = '1.3'


class Memoize:
    """
    Cache the return value of a method

    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.

    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object):
        @memoize
        def add_to(self, arg):
            return self + arg
    Obj.add_to(1) # not enough arguments
    Obj.add_to(1, 2) # returns 3, result is not cached

    See http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/
    """

    def __init__(self, func):
        """
        Object constructor.
        :param func: The decorated callable
        """
        self.func = func

    def __get__(self, obj, _):
        """
        Return cached result (if already computed) or
        the result returned by the cached function.
        """
        if obj is None:
            return self.func
        return functools.partial(self, obj)

    def __call__(self, *args, **kw):
        """
        Cache function return value.
        """
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(list(kw.items())))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res
