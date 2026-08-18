import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from number_utils import is_prime, dedupe_preserve_order, running_total


def test_is_prime():
    assert is_prime(7) is True
    assert is_prime(4) is False
    assert is_prime(2) is True


def test_dedupe_preserve_order():
    assert dedupe_preserve_order([3, 1, 3, 2, 1, 2]) == [3, 1, 2]


def test_running_total():
    assert running_total([1, 2, 3]) == [1, 3, 6]
