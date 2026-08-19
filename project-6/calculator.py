"""A tiny statistics/calculator module used for the Project 6 PR-review exercise.

The module intentionally contains a single, easy-to-detect planted bug so that
an automated OpenCode PR review can demonstrate finding it. The unit tests that
ship with this project PASS (they do not exercise the buggy function), which
means the bug is *not* caught by CI — it must be caught by a code review.
"""


def mean(values):
    """Return the arithmetic mean of a non-empty list of numbers."""
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) / len(values)


def divide(numerator, denominator):
    """Return numerator / denominator."""
    return numerator / denominator


def max_value(values):
    """Return the largest value in a non-empty list.

    PLANTED BUG: the comparison is inverted. The loop keeps the *smallest*
    value instead of the largest because it updates `result` when the next
    value is *less than* the current result. The condition should be
    ``if v > result``.
    """
    if not values:
        raise ValueError("max_value() requires at least one value")
    result = values[0]
    for v in values[1:]:
        if v < result:  # BUG: should be `v > result`
            result = v
    return result
