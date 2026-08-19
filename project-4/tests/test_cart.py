import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cart import CartItem, subtotal, apply_discount, total


def test_no_discount_below_threshold():
    items = [CartItem("a", 10, 5)]  # subtotal 50
    assert total(items) == 50.00


def test_discount_above_threshold():
    items = [CartItem("a", 20, 6)]  # subtotal 120
    assert total(items) == 108.00


def test_discount_at_exactly_threshold():
    items = [CartItem("a", 25, 4)]  # subtotal 100 exactly
    assert total(items) == 90.00


def test_empty_cart():
    assert total([]) == 0.00
