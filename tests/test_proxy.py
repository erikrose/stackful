"""Tests for a representative subset of magic method overrides."""

from nose import SkipTest
from nose.tools import eq_

from stacked import Proxy


def sixProxy():
    return Proxy(6, 0)

def strProxy():
    return Proxy('fred', 'orig')


def test_add():
    eq_(sixProxy() + 1, 7)

def test_radd():
    eq_(1 + sixProxy(), 7)

def test_list_comparison():
    """Make sure proxies are convincing enough to fool list comparison.

    Python compares lists element by element.

    """
    eq_([sixProxy()], [6])
    assert [sixProxy()] == [6]
    eq_([[sixProxy()]], [[6]])

def test_attr_passthrough():
    """Make sure normal attr access falls through to the contained object."""
    assert strProxy().startswith('fr')

def test_isinstance():
    raise SkipTest
    assert isinstance(sixProxy(), int)

def test_issubclass():
    raise SkipTest
    assert issubclass(type(strProxy()), basestring)
