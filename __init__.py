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
    """Metaclass for Proxies that passes special method lookup through to an instance var on the created class

    As explained in
    http://docs.python.org/reference/datamodel.html#new-style-special-lookup,
    __getattribute__ is not consulted when looking up special methods
    implicitly. For example, when len(obj) is called, neither
    obj.__getattribute__ nor type(obj).__getattribute__ is consulted.
    Therefore, we must explicitly define __len__ and all other special methods
    on the Proxy class. This metaclass lets us do this in a loop rather than
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
                underlying_method = getattr(
                    inner_obj,
                    method_name,
                    getattr(type(inner_obj), method_name))
                return underlying_method(*args, **kwargs)
            return fallthrough
        super(FallthroughMethods, cls).__init__(name, bases, attributes)
        for method_name in ['__eq__', '__neq__', '__abs__', '__pos__', '__invert__', '__neg__', '__radd__', '__add__', '__rsub__', '__sub__', '__rdiv__', '__div__', '__rmul__', '__mul__', '__rand__', '__and__', '__ror__', '__or__', '__rxor__', '__xor__', '__rlshift__', '__lshift__', '__rrshift__', '__rshift__', '__rmod__', '__mod__', '__rdivmod__', '__divmod__', '__rtruediv__', '__truediv__', '__rfloordiv__', '__floordiv__', '__rpow__', '__pow__', '__cmp__', '__str__', '__unicode__', '__complex__', '__int__', '__long__', '__float__', '__oct__', '__hex__', '__hash__', '__len__', '__iter__', '__delattr__', '__setitem__', '__delitem__', '__setslice__', '__delslice__', '__getitem__', '__call__', '__getslice__', '__nonzero__']:
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
