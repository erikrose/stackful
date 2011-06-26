from threading import Thread
from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_, assert_raises

import stacked
from stacked.tests import other_module


# def NO_test_existing_var():
#     """Try overriding a non-stacked var."""
#     global g
#     eq_(g, 0)  # Assert no other test screwed it up. Become a setUp() if we grow more tests.
#     with stacked.var('g', 1):
#         eq_(_get_g(), 1)
#     eq_(g, 0)

    # Maybe try to make one of these possible later:

    # Or...
    #with stacked.var('g'):
        #g = 'new'  # Can't do it; can't override assignment. :-(

    # Or patch an instruction onto the end of the function that resets the value of g. And still provide the "with" syntax for stacking within just part of a function.
    #g = stacked.var(7)  # Can look upward from within var(), see what the lval symbol name was, make it into a stack, and push the new val onto it. But then when you try to read g, you get this weird stack object. Fail. Ah, but if I can tail-patch the function by either editing its code or by inserting a pop() frame into the stack above it.... co_code attrs are immutable, and there's no in-Python (or in-C, for that matter) way I can find to mutate the stack. Ah, but we can make the weird stack object implement every __op__ method there is so that when you actually use it, it produces the correct value. But we still have no way of

    # Oh damn, threadlocals make you do attr access, so that's out. We have no hook for computation. Ah, but what can you really do with an obj? Apply binary and unary ops, do attr accesss, call them, etc. And all those are overridable! Hmm.


def _get_g():
    return g


class ScopeTests(TestCase):
    def setUp(self):
        global g
        g = 0

    def test_global(self):
        global g
        with stacked.var('g', 1):
            eq_(_get_g(), 1)
        eq_(g, 0)

    def tearDown(self):
        global g
        del g

    # def test_threads():
    #     global g
    #     things = []
    #
    #     def get_global():
    #         things.append(g)
    #
    #     eq_(g, 0)
    #     with stacked.var('g', 1):
    #         t = Thread(target=get_global)
    #         t.start()
    #         t.join()
    #         eq_(0 + 1, things[0] + 1)


def test_new_global():
    """Make sure stacking works atop uninitialized globals."""
    global g
    assert_raises(NameError, lambda: g)
    with stacked.var('g', 2):
        eq_(_get_g(), 2)
    assert_raises(NameError, lambda: g)

def test_other_modules():
    """Make sure globals in other modules work."""
    raise SkipTest
    # TODO: Figure out how to do this. Perhaps we should look at f_locals
    # first. We can't mutate what's assigned to hash keys, but we should be
    # able to mutate the value objects themselves if they're mutable. Or maybe
    # we should pass 'other_module.some_global' in.
    the_global = other_module.some_global
    with stacked.var('the_global', 8):
        eq_(other_module.some_global, 8)
    eq_(other_module.some_global, orig)

# def test_closure():
#     c = 0
#     def closure():
#         return c
#     eq_(closure(), 0)
#     with stacked.var('c', 1):
#         
