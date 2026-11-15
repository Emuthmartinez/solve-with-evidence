"""Rounding and percentages for amounts in integer cents."""
import math


def round_cents(value):
    """Round a fractional number of cents to whole cents. Halves round up, not to even (BILL-731)."""
    return math.floor(value + 0.5)


def percent_of(amount, percent):
    """`percent` per cent of `amount` cents, in whole cents.

    `percent` is a number or a decimal string such as '19' or '8.75'.
    """
    return round_cents(amount * (float(percent) / 100))
