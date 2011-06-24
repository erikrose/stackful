from nose.tools import eq_
import stacked


g = 0

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


def test_global():
    global g
    eq_(g, 0)
    with stacked.var('g', 1):
        eq_(_get_g(), 1)
    eq_(g, 0)


# def test_closure():
#     c = 0
#     def closure():
#         return c
#     eq_(closure(), 0)
#     with stacked.var('c', 1):
#         