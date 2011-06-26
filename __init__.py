"""Dynamically scoped (call-stack-based) variables for Python"""

from inspect import currentframe
from lazypy import Promise
import threading


NoSuchThing = object()


class var(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __enter__(self):
        """Save original value of var. Rebind var to a Proxy."""
        frame = currentframe().f_back
        self.orig = frame.f_globals.get(self.name, NoSuchThing)
        frame.f_globals[self.name] = Proxy(self.value, self.orig, self.name)
        # Too bad it won't let us mutate f_locals.
        del frame

    def __exit__(self, a, b, c):
        """Rebind var in upper frame to its original value."""
        frame = currentframe().f_back
        if self.orig is NoSuchThing:
            del frame.f_globals[self.name]
        else:
            frame.f_globals[self.name] = self.orig
        del frame


def my_getattribute(self, name):
    # TODO: Make ___value a threadlocal bunch of stacks.
    return self.___value if name == '___value' else getattr(self.___value, name)


class StackedMetaclass(type):
    def __init__(klass, name, bases, attributes):
        attr = '__getattribute__'
        if attr not in attributes:
            setattr(klass, attr, my_getattribute)
        super(StackedMetaclass, klass).__init__(name, bases, attributes)


class Proxy(Promise):
    """Dynamically-scoped (and thus also thread-local) proxy to a value

    Acts just like the passed-in `value` in the current thread and like the
    separately passed-in `original` value in other threads. Since we don't have
    the opportunity to initiate a thread-local lookup when I am referenced, be
    sneaky and do the lookup when I am operated upon in any way. This should
    catch the vast majority of actual uses.

    The magic methods are defined in the metaclass because Python looks for
    some of them, like __instancecheck__, only on the metaclass.

    """
    def __init__(self, value, orig, name='<unspecified>'):
        """Constructor

        Args:
            value: the value to expose in the current
            original: value to fall back to in other threads.

        """
        self.___value = threading.local()
        self.___value.value = value
        self.orig = orig
        self.name = name

    def __force__(self):
        ret = self.___value.__dict__.get('value', self.orig)  # TODO: What happens when you try to read a threadlocal that's not defined in this thread?
        if ret is NoSuchThing:  # We stacked on top of an uninitialized global.
            raise NameError("name '%s' is not defined in this thread" % self.name)
        else:
            return ret
