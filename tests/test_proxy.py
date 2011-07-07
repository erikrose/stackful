"""Unit tests for Proxy objects

Tests for a representative subset of magic method overrides.

"""
from nose import SkipTest
from nose.tools import eq_

from stacked import Proxy
from stacked.tests import fails


def six_proxy():
    return Proxy(6, 0)

def str_proxy():
    return Proxy('fred', 'orig')


def test_add():
    eq_(six_proxy() + 1, 7)

def test_radd():
    eq_(1 + six_proxy(), 7)

def test_lt():
    assert six_proxy() < 7

def test_list_comparison():
    """Make sure proxies are convincing enough to fool list comparison.

    Python compares lists element by element.

    """
    eq_([six_proxy()], [6])
    assert [six_proxy()] == [6]
    eq_([[six_proxy()]], [[6]])

def test_attr_passthrough():
    """Make sure normal attr access falls through to the contained object."""
    assert str_proxy().startswith('fr')

def test_isinstance():
    """Make sure a proxied object pretends to be an instance of that object's type."""
    six = six_proxy()
    assert isinstance(six, int)
    assert isinstance(str_proxy(), basestring)
    # This seems to be how isinstance(6, int) works:
    assert type(six).__instancecheck__(six)

def test_issubclass():
    # TODO: Perhaps actually create a new class for each stacked.var() call,
    # one that defines __subclasscheck__ as desired.
    raise SkipTest
    eq_(issubclass(basestring, type(str_proxy())),
        issubclass(basestring, type('abc')))
#     eq_(issubclass(type(str_proxy()), basestring),
#         issubclass(type('abc'), basestring))

def test_fallthrough_to_implicit_methods():
    """Make sure we don't call through to a magic method on the proxied object if it isn't the sort of method that has to be explicitly defined.

    In other words, though we define all the magic methods, if the same method
    isn't actually defined on the proxied object, act just as if we hadn't
    defined it either, falling back to builtins if they exist.

    """
    try:
        str_proxy().smoo
    except AttributeError, e:
        eq_(e.args[0], "'str' object has no attribute 'smoo'")
    else:
        raise AssertionError("Nonexistent attribute access didn't raise an AttributeError.")

@fails
def test_type():
    """Make sure proxying a type doesn't crash."""
    eq_(repr(Proxy(int, 6)), "<type 'int'>")

def test_distinguish_builtins_from_attr_access():
    """Accessing __getattr__ on a proxy to an object without it should throw an error.

    Likewise for __lt__ or any other magic method.

    """
    p = Proxy(object(), 6)
    try:
        p.__getattr__
    except AttributeError, e:
        eq_(e.args[0], "'object' object has no attribute '__getattr__'")
    else:
        raise AssertionError("Nonexistent attribute access didn't raise an AttributeError.")

# Probably can't make this work.
def test_hasattr_falsity():
    """hasattr() should be false on a special method if the original object didn't have it."""
    assert not hasattr(six_proxy(), '__len__')

# @fails
# def test_is():
#     assert six_proxy() is 6

def test_descriptors():
    """Make sure descriptor calls fall through to proxied object."""
    class DescriptorHaver(object):
        @property
        def thing(self):
            return 'smoo'
    p = Proxy(DescriptorHaver(), None)
    eq_(p.thing, 'smoo')

def test_dir():
    # I think this works just by virtue of passing __dict__ through.
    eq_(dir(six_proxy()), dir(6))

def test_metaclass_delegation():
    """Make sure attributes of classes properly delegate to custom metaclasses.

    (This comes into play when proxying classes and has nothing to do with
    instances.)

    """
    class Meta(type):
        def __len__(*args):
            return 33

    class Class(object):
        __metaclass__ = Meta

    eq_(len(Class), 33)
    eq_(len(Proxy(Class, None)), 33)

@fails
def test_docstring():
    """Fallthrough methods shouldn't obscure docstrings from wrapped methods."""
    class Thing(object):
        def __len__(self):
            """Length!"""
            return 19

    eq_(Proxy(Thing(), None).__doc__, 'Length!')
