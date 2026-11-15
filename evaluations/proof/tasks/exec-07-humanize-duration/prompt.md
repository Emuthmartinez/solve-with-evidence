Write `solution.py` with one function:

```python
def humanize(seconds: float, max_units: int = 2) -> str:
```

It describes a duration in words, such as `"1 day and 2 hours"`. `seconds` is an int or a float. `max_units` is an int.

The units, largest first, are week (604800 seconds), day (86400), hour (3600), minute (60) and second (1).

Rules:

1. Raise `ValueError` when `max_units` is less than 1, or when `seconds` is NaN or infinite.
2. Let x be the absolute value of `seconds`, taken exactly: use the exact value the float holds, as `fractions.Fraction(seconds)` gives it, not a rounded decimal or float arithmetic. Test inputs such as 0.5, 2.5 and 3599.5 are exact in binary, so their halves are exact halves.
3. The leading unit is the largest unit whose size is at most x. If x is less than 1, the leading unit is second.
4. The window is the leading unit followed by the next `max_units - 1` smaller units, taken from the list above. The window stops at second, so it can hold fewer than `max_units` units. Its smallest unit is the rounding unit.
5. Round x to a whole number of rounding units. A value exactly halfway rounds up (2.5 becomes 3, 3.5 becomes 4). Never round half to even.
6. Write the rounded total in weeks, days, hours, minutes and seconds, largest first, taking as many of each unit as fit. Rounding can carry into larger units, even past the leading unit: with two units, 3599.5 seconds is 59 minutes and 59.5 seconds, the seconds round to 60, and the result is `"1 hour"`, never `"59 minutes and 60 seconds"` or `"60 minutes"`.
7. Output the units whose count is not zero, largest first. A unit inside the window whose count is zero is left out. If every count is zero, the output is `"0 seconds"`.
8. Each part is the count in plain digits, a space and the unit name. The name is singular when the count is exactly 1 and takes a final `s` otherwise: `"1 day"`, `"2 days"`, `"0 seconds"`.
9. One part is output alone. Two parts are joined by `" and "`. Three or more parts are joined by `", "`, except that the last two are joined by `" and "`, with no comma before `and`: `"1 week, 1 day and 1 hour"`.
10. When `seconds` is negative and the output is not `"0 seconds"`, prefix `"minus "`. Rounding works on x, the absolute value, so `-0.5` gives `"minus 1 second"` and `-0.25` gives `"0 seconds"`.

Examples:

```python
humanize(3599.5)   # '1 hour'
humanize(93784)    # '1 day and 2 hours'
humanize(-90, 1)   # 'minus 2 minutes'
```

In the second example, 93784 seconds is 1 day, 2 hours, 3 minutes and 4 seconds. The window is day and hour, and the 3 minutes 4 seconds round down to 0 hours. In the third, the window is minute alone, and 1.5 minutes round up to 2.

Use the Python standard library only.
