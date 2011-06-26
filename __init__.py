"""Dynamically scoped (call-stack-based) variables for Python"""

from inspect import currentframe
import threading


no_such_thing = object()


class var(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __enter__(self):
        """Save original value of var. Rebind var to a Proxy."""
        frame = currentframe().f_back
        self.orig = frame.f_globals.get(self.name, no_such_thing)
        frame.f_globals[self.name] = Proxy(self.value, self.orig, self.name)
        # Too bad it won't let us mutate f_locals.
        del frame

    def __exit__(self, a, b, c):
        """Rebind var in upper frame to its original value."""
        frame = currentframe().f_back
        if self.orig is no_such_thing:
            del frame.f_globals[self.name]
        else:
            frame.f_globals[self.name] = self.orig
        del frame


# def _attribute_of_threadlocal(self, attr):
#     # TODO: Make _threadlocals_from_stacked a threadlocal bunch of stacks. [Ed: Probably
#     # unnecessary. We can just let Proxies contain other Proxies.]
#     threadlocals = object.__getattribute__(self, '_threadlocals_from_stacked')
#     orig         = object.__getattribute__(self, 'orig')
#
#     obj = threadlocals.__dict__.get('value', orig)  # TODO: What does a local() do when you try to read a threadlocal that's not defined in this thread?
#     if obj is no_such_thing:
#         name = object.__getattribute__(self, 'name')
#         raise NameError("You stacked on top of uninitialized global '%s', and "
#                         "now you're trying to read it in a thread where it's "
#                         "still uninitialized." % name)
#     else:
#         return getattr(obj, attr)
#

class FallthroughMethods(type):
    """Metaclass for Proxies that defines all special methods

    I cause all special method lookup to be delegated transparently to an
    instance var on the created class.

    As explained in
    http://docs.python.org/reference/datamodel.html#new-style-special-lookup,
    __getattribute__ is not consulted when looking up special methods
    implicitly. For example, when len(obj) is called, neither
    obj.__getattribute__ nor type(obj).__getattribute__ is consulted.
    Therefore, we must explicitly define __len__ and all other special methods
    on the Proxy class. This metaclass lets us do so in a loop rather than
    typing a lot of repetitive code (or paying function call penalties if we
    were to factor up).

    """
    def __init__(cls, name, bases, attributes):
        def fallthrough_method(method_name):
            # TODO: Use @wrap?
            def fallthrough(self, *args, **kwargs):
                """Pass through a method call to the object within a Proxy.

                Find the method on the object contained by the Proxy or,
                failing that, on its type. (8.__eq__ does not exist, but
                type(8).__eq__ does.) Call that method with whatever args were
                passed to me.

                """
                inner_obj = object.__getattribute__(self, '_threadlocals_from_stacked').value

                # If the method is __del__(), tolerate its absence from both
                # the instance and the type; it just plain isn't around if you
                # don't define it. TODO: optimize by figuring this out at class
                # definition time.
                nop_or_not = [lambda *args, **kwargs: None] if method_name == '__del__' else []

                underlying_method = getattr(
                    inner_obj,
                    method_name,
                    getattr(type(inner_obj), method_name, *nop_or_not))
                return underlying_method(*args, **kwargs)
            return fallthrough

        super(FallthroughMethods, cls).__init__(name, bases, attributes)

        # These are basically all the special methods from
        # http://docs.python.org/reference/datamodel.html#new-style-special-lookup.
        #
        # TODO: Some of these might be sufficiently passed through by our
        # __getattribute__(). Write tests and pare these down.
        #
        # TODO: We apparently aren't allowed to write to __instancecheck__ and
        # __subclasscheck__. __setattr__ was causing test failures:
        # AttributeError: 'Proxy' object has no attribute
        # '_threadlocals_from_stacked'.
        for method_name in ['call', 'getattr', 'delattr', 'getitem', 'del',
            'repr', 'str', 'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'cmp', 'hash',
            'rcmp', 'nonzero', 'len', 'unicode', 'get', 'set', 'delete',
            'getslice', 'setitem', 'delitem', 'add', 'radd', 'iadd', 'mul',
            'rmul', 'imul', 'coerce', 'contains', 'iter', 'reversed',
            'setslice', 'delslice', 'sub', 'floordiv', 'mod', 'divmod', 'pow',
            'lshift', 'rshift', 'and', 'xor', 'or', 'truediv', 'div', 'rsub',
            'rdiv', 'rtruediv', 'rfloordiv', 'rmod', 'rdivmod', 'rpow',
            'rlshift', 'rrshift', 'rand', 'rxor', 'ror', 'isub', 'idiv',
            'itruediv', 'ifloordiv', 'imod', 'ipow', 'ilshift', 'irshift',
            'iand', 'ixor', 'ior', 'neg', 'pos', 'abs', 'invert', 'complex',
            'int', 'long', 'float', 'oct', 'hex', 'index', 'enter', 'exit']:
            method_name = '__%s__' % method_name
            setattr(cls, method_name, fallthrough_method(method_name))


class Proxy(object):
    """Dynamically-scoped (and thus also thread-local) proxy to a value

    Acts just like the passed-in `value` in the current thread and like the
    separately passed-in `original` value in other threads. Since we don't have
    the opportunity to initiate a thread-local lookup when I am referenced, be
    sneaky and do the lookup when I am operated upon in any way. This should
    catch the vast majority of actual uses.

    The magic methods are defined in the metaclass because Python looks for
    some of them, like __instancecheck__, only on the metaclass.

    """
    __metaclass__ = FallthroughMethods

    def __init__(self, value, orig, name='<unspecified>'):
        """Constructor

        Args:
            value: the value to expose in the current
            original: value to fall back to in other threads.

        """
        self._threadlocals_from_stacked = threading.local()
        object.__getattribute__(self, '_threadlocals_from_stacked').value = value
        self.orig = orig
        self.name = name

    def __getattribute__(self, attr):
        # TODO: Make _threadlocals_from_stacked a threadlocal bunch of stacks.
        # [Ed: Probably unnecessary. We can just let Proxies contain other
        # Proxies.]
        threadlocals = object.__getattribute__(self, '_threadlocals_from_stacked')
        try:
            # TODO: Probably don't need this try anymore.
            obj = threadlocals.value  # TODO: What does a local() do when you try to read a threadlocal that's not defined in this thread?
        except AttributeError:
            obj = object.__getattribute__(self, 'orig')

        if obj is no_such_thing:
            name = object.__getattribute__(self, 'name')
            raise NameError("You stacked on top of uninitialized global '%s', and "
                            "now you're trying to read it in a thread where it's "
                            "still uninitialized." % name)
        else:
            return getattr(obj, attr)
