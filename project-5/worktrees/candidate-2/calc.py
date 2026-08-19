#!/usr/bin/env python3
"""A tiny calculator with a few deliberate bugs for the fix-and-review demo."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b  # BUG: off-by-one


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b


if __name__ == "__main__":
    print(add(2, 3), subtract(5, 3), multiply(3, 4), divide(7, 2))
