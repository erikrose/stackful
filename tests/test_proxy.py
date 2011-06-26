"""Tests for a representative subset of magic method overrides."""

from nose import SkipTest
from nose.tools import eq_

from stacked import Proxy


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
    assert isinstance(six_proxy(), int)

def test_issubclass():
    raise SkipTest  # Still fails.
    assert issubclass(type(str_proxy()), basestring)
