"""Unit tests for the calculator module.

These tests are intentionally limited: they cover `mean` and `divide` but do
NOT cover `max_value`. As a result the planted bug in `max_value` is not
detected by the test suite — it must be caught by the automated OpenCode code
review triggered on pull requests.
"""

from calculator import divide, mean


def test_mean_basic():
    assert mean([1, 2, 3]) == 2.0
    assert mean([10, 20, 30, 40]) == 25.0


def test_mean_single():
    assert mean([42]) == 42.0


def test_divide_basic():
    assert divide(6, 3) == 2.0
    assert divide(1, 4) == 0.25


def test_mean_empty_raises():
    import pytest

    with pytest.raises(ValueError):
        mean([])
