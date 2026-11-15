"""Rounding and percentages for amounts in integer cents."""
from fractions import Fraction


def round_cents(value):
    """Round an exact number of cents, an int or a Fraction, to whole cents.

    A value exactly halfway between two cents goes away from zero, whatever its sign.
    """
    value = Fraction(value)
    whole = (2 * abs(value.numerator) + value.denominator) // (2 * value.denominator)
    return -whole if value < 0 else whole


def percent_of(amount, percent):
    """`percent` per cent of `amount` cents, in whole cents.

    `percent` is a decimal string such as '19' or '8.75', read as an exact decimal.
    """
    return round_cents(amount * Fraction(percent) / 100)
