"""Dynamically scoped (call-stack-based) variables for Python"""

from inspect import currentframe
import operator
import threading
from warnings import warn


_no_such_thing = object()


class var(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __enter__(self):
        """Save original value of var. Rebind var to a Proxy."""
        frame = currentframe().f_back
        self.orig = frame.f_globals.get(self.name, _no_such_thing)
        self.proxy = frame.f_globals[self.name] = Proxy(self.value, self.orig, self.name)
        # Too bad it won't let us mutate f_locals.
        del frame

    def __exit__(self, a, b, c):
        """Rebind var in upper frame to its original value."""
        frame = currentframe().f_back
        if frame.f_globals[self.name] is not self.proxy:
            # Unfortunately, we can't intercept rebindings.
            warn("Someone rebound the stackful global '%s', defeating its stackfulness.")
        if self.orig is _no_such_thing:
            del frame.f_globals[self.name]
        else:
            frame.f_globals[self.name] = self.orig
        del frame


_nop = lambda *args, **kwargs: None
# Basically, [x for x in [double-underscore methods] if hasattr(__builtins__, x)]:
_implicit_methods = [('getattr', getattr),
                     ('setattr', setattr),
                     ('delattr', delattr),
                     ('repr', repr),
                     ('cmp', cmp),
                     ('hash', hash),
                     ('len', len),
                     ('coerce', coerce),
                     # TODO: more here
                     ('del', _nop),
                     ('eq', operator.eq),
                     ('lt', operator.lt)]
_implicit_methods = dict(('__%s__' % name, meth) for name, meth in _implicit_methods)


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
    were to factor up). Yes, we could have used a class decorator, but HEY,
    METACLASSES!

    """
    def __init__(cls, name, bases, attributes):
        def fallthrough_method(method_name):
            # TODO: Use functools.wraps()?
            def fallthrough(self, *args, **kwargs):
                """Pass through a method call to the object within a Proxy.

                Find the method on the object contained by the Proxy or,
                failing that, on its type. (8.__eq__ does not exist, but
                type(8).__eq__ does.) Failing that, try an equivalent builtin
                method which the interpreter would ordinarily implicitly
                dispatch to. Call that method with whatever args were passed to
                me.

                """
                # On a call to a magic method, see if it has a builtin equivalent. If it does, call that on the proxied object. That'll dispatch to instance and type and builtin as appropriate. The trouble with this is that it doesn't distinguish between calling getattr(proxy, 'smoo') and proxy.__getattr__('smoo'). The latter should throw an AttributeError if the proxied obj doesn't define __getattr__. But hey, we actually *can* distinguish them: in proxy.__getattr__, the only thing we see is a call to proxy.__getattribute__('__getattr__'). In proxy.d, we see only proxy.__getattribute__('d').

                threadlocals = object.__getattribute__(self, '_threadlocals_from_stacked')
                try:
                    inner_obj = threadlocals.value
                except AttributeError:
                    inner_obj = object.__getattribute__(self, 'orig')

                # Get the underlying method if it exists on the instance or its
                # type (which would be a class in the case of an instance, a
                # metaclass in the case of a class):
                try:
                    bound_method = getattr(inner_obj, method_name)
                except AttributeError:
                    # The method wasn't defined on the instance or its
                    # type. If it has a builtin implicit implementation
                    # like getattr, use that:
                    unbound_method = _implicit_methods.get(method_name)
                    if unbound_method:
                        return unbound_method(inner_obj, *args, **kwargs)
                    else:
                        # The method was neither defined nor implicitly
                        # supported. It's a bona fide missing attr.
                        raise
                else:
                    return bound_method(*args, **kwargs)
            return fallthrough

        super(FallthroughMethods, cls).__init__(name, bases, attributes)

        # These are basically all the special methods from
        # http://docs.python.org/reference/datamodel.html#new-style-special-lookup.
        #
        # TODO: Some of these might be sufficiently passed through by our
        # __getattribute__(). Write tests and pare these down.
        #
        # TODO: We apparently aren't allowed to write to __subclasscheck__ (or
        # __instancecheck__). __subclasscheck__ goes the wrong way for most
        # uses, anyway: I don't care to assert that basestring is a subclass of
        # me; I want to assert I'm a subclass of basestring.
        #
        # We actually don't need to override __instancecheck__; when you call
        # isinstance(), the interpreter looks up the type of the object by
        # looking at __class__, and __getattribute__ suffices to delegate that
        # to the proxied object.
        for method_name in ['call', 'getattr', 'setattr', 'delattr', 'getitem',
            'del', 'repr', 'str', 'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'cmp',
            'hash', 'rcmp', 'nonzero', 'len', 'unicode', 'get', 'set',
            'delete', 'getslice', 'setitem', 'delitem', 'add', 'radd', 'iadd',
            'mul', 'rmul', 'imul', 'coerce', 'contains', 'iter', 'reversed',
            'setslice', 'delslice', 'sub', 'floordiv', 'mod', 'divmod', 'pow',
            'lshift', 'rshift', 'and', 'xor', 'or', 'truediv', 'div', 'rsub',
            'rdiv', 'rtruediv', 'rfloordiv', 'rmod', 'rdivmod', 'rpow',
            'rlshift', 'rrshift', 'rand', 'rxor', 'ror', 'isub', 'idiv',
            'itruediv', 'ifloordiv', 'imod', 'ipow', 'ilshift', 'irshift',
            'iand', 'ixor', 'ior', 'neg', 'pos', 'abs', 'invert', 'complex',
            'int', 'long', 'float', 'oct', 'hex', 'index', 'enter', 'exit']:
            method_name = '__%s__' % method_name
            setattr(cls, method_name, fallthrough_method(method_name))


class Proxy(object):  # Assumptions about what this subclasses are everywhere.
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
        # This looks horrible but isn't. We're just dodging our
        # __getattribute__ and any __setattr__ on the contained object in order
        # to set some attrs on the Proxy object itself.
        my_dict = object.__getattribute__(self, '__dict__')
        my_dict['_threadlocals_from_stacked'] = threading.local()
        my_dict['_threadlocals_from_stacked'].value = value
        my_dict['orig'] = orig
        my_dict['name'] = name

    def __getattribute__(self, attr):
        # TODO: Make _threadlocals_from_stacked a threadlocal bunch of stacks.
        # [Ed: Probably unnecessary. We can just let Proxies contain other
        # Proxies.]
        threadlocals = object.__getattribute__(self, '_threadlocals_from_stacked')
        try:
            # When you have a local() and try to read an attr that's not
            # defined in this thread, you get an AttributeError.
            obj = threadlocals.value
        except AttributeError:
            obj = object.__getattribute__(self, 'orig')

        if obj is _no_such_thing:
            name = object.__getattribute__(self, 'name')
            raise NameError("You stacked on top of uninitialized global '%s', and "
                            "now you're trying to read it in a thread where it's "
                            "still uninitialized." % name)
        else:
            return getattr(obj, attr)
