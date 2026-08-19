"""
Shopping cart pricing module.

Spec: Discount of 10% applies when the cart subtotal is $100 OR MORE
(i.e. at the boundary subtotal == 100.00 the discount MUST be applied).
"""

class CartItem:
    def __init__(self, name, unit_price, quantity):
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity

    def line_total(self):
        return self.unit_price * self.quantity


def subtotal(items):
    return sum(item.line_total() for item in items)


def apply_discount(subtotal_amount):
    if subtotal_amount >= 100:
        return subtotal_amount * 0.90
    return subtotal_amount


def total(items):
    sub = subtotal(items)
    discounted = apply_discount(sub)
    return round(discounted, 2)
