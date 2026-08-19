#!/usr/bin/env python3
"""Tiny test suite for the sample calculator.

Exit code 0 = all checks passed (PASS).
Exit code 1 = at least one check failed (FAIL).

reviewer.sh runs this file; its exit code is the grade for a candidate.
"""
from calc import add, subtract, multiply, divide


def main():
    assert add(2, 3) == 5, "add(2, 3) should be 5"
    assert subtract(5, 3) == 2, "subtract(5, 3) should be 2"
    assert multiply(3, 4) == 12, "multiply(3, 4) should be 12"
    assert divide(7, 2) == 3.5, "divide(7, 2) should be 3.5"
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
