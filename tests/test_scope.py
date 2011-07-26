from threading import Thread, Lock
from unittest import TestCase
from warnings import catch_warnings

from nose import SkipTest
from nose.tools import eq_, assert_raises

from stackful import stackful
from stackful.tests import other_module
from stackful.tests.other_module import some_immutable


def _get_g():
    """Return the global g but from a deeper stack frame."""
    return g

def _set_g():
    global g
    g = 'yeah'


class ModuleGlobalTests(TestCase):
    """Tests that may create a global ``g`` in this module

    Makes sure they don't leave it lying around.

    """
    def tearDown(self):
        global g
        try:
            del g
        except NameError:
            pass

    def test_global(self):
        global g
        g = 0
        with stackful('g', 1):
            eq_(_get_g(), 1)
        eq_(g, 0)

    def test_multi_level(self):
        global g
        g = 0
        with stackful('g', 1):
            eq_(_get_g(), 1)
            with stackful('g', 2):
                eq_(_get_g(), 2)
            eq_(_get_g(), 1)
        eq_(g, 0)

    def test_threads(self):
        """Make sure stackful vars are really thread-specific."""
        global g
        g = 0
        things = []
        lock = Lock()

        def get_global():
            lock.acquire()
            # Operate on g to collapse its quantum superposition:
            things.append(g + 1)

        with stackful('g', 1):
            t = Thread(target=get_global)  # TODO: Right now, the thread sees it as 0. Should it be 1?
            lock.acquire()
            t.start()
            with stackful('g', 9):
                lock.release()
                t.join()
                eq_(things[0], 1)

    def test_rebinding_warning(self):
        """We can't intercept rebinding a stackful variable downstream like Lisp does.

        We should scream if someone tries.

        """
        global g
        g = 0
        with catch_warnings(record=True) as warnings:
            with stackful('g', 8):
                _set_g()
                eq_(g, 'yeah')
        eq_(len(warnings), 1)
        assert 'stackfulness' in warnings[0].message.args[0]
        # var() restores the variable on exit despite the rebinding. This may
        # or may not be a good idea.
        eq_(g, 0)

    def test_copying_proxies_to_immutables(self):
        """Gee, I wonder how this acts. What should it even do? It should act like it's copying an immutable, not like it's getting an obj ref."""
        global g
        g = 0
        with stackful('g', 7):
            seven = g  # Should act as if it's copying the 7.
            with stackful('g', 8):
                eight = g
        eq_(seven, 7)
        eq_(eight, 8)
        eq_(g, 0)

    def test_new_global(self):
        """Make sure stacking works atop uninitialized globals."""
        global g
        assert_raises(NameError, lambda: g)
        with stackful('g', 2):
            eq_(_get_g(), 2)
        assert_raises(NameError, lambda: g)


def test_other_modules():
    """Make sure globals in other modules work."""
    # TODO: Figure out how to do this. Perhaps we should look at f_locals
    # first. We can't mutate what's assigned to hash keys, but we should be
    # able to mutate the value objects themselves if they're mutable. Or maybe
    # we should pass 'other_module.some_immutable' in.
    orig = some_immutable
    # Try with imported symbol:
    with stackful('some_immutable', 8):
        eq_(some_immutable, 8)
    eq_(some_immutable, orig)

    # And with imported module:
    # with stackful('other_module.some_immutable', 8):
    #     eq_(other_module.some_immutable, 8)
    # eq_(other_module.some_immutable, orig)

# def test_closure():
#     c = 0
#     def closure():
#         return c
#     eq_(closure(), 0)
#     with stackful('c', 1):
#
