"""Dynamically scoped (call-stack-based) variables for Python"""

# Goals:
#  * Backward-compatible with vars not defined with the framework

from inspect import currentframe

# _internal_modules = set([__module__])


def _assignment_var():
    """Return the name of the symbol to which I'm being assigned in the first upward frame above this lib."""
    # TODO: Actually loop through the frames until we get out of this lib.


def _deepest_frame_not_mine():
    frame = currentframe()
    try:
        while frame.f_back:
            frame = frame.f_back  # TODO: Make sure the old value of frame gets GCd.
            if getmodule(frame) not in _internal_modules:
                return frame
        raise NotImplementedError('Really? No frame outside the stacked package?')
    finally:
        # Break cycles so we don't have to fall back on the cycle detector, which might take a long time. Recommended by http://docs.python.org/lib/inspect-stack.html.
        del frame


def _var_from_outside(name):
    """Return the value of the named symbol from the newest frame not from this library."""    
    frame = _deepest_frame_not_mine()
    try:
        return frame.f_globals[name]  # Used to return locals preferentially, but I can't mutate those.
    finally:
        del frame


class var(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __enter__(self):
        """Save orig value of var. Rebind var to a StackedPromise."""
        frame = currentframe().f_back  # TODO: Use _deepest_frame_not_mine().
        self.orig = frame.f_globals[self.name]
        frame.f_globals[self.name] = self.value
        del frame
    
    def __exit__(self, a, b, c):
        """Rebind var in upper frame to its original value."""        
        frame = currentframe().f_back
        frame.f_globals[self.name] = self.orig
        del frame


def my_getattribute(self, name):
    # TODO: Make _original a threadlocal bunch of stacks.
    return self.___original if name == '___original' else getattr(self.___original, name)


class StackedMetaclass(type):
    def __init__(klass, name, bases, attributes):
        attr = '__getattribute__'
        if attr not in attributes:
            setattr(klass, attr, my_getattribute)
        super(StackedMetaclass, klass).__init__(name, bases, attributes)


class StackedPromise(object):
    """Dynamically-scoped lazy proxy to a value"""

    __metaclass__ = StackedMetaclass

    def __init__(self, original):
        self.___original = original

    def __force__(self):
        return self.original

    # def __getattribute__(
