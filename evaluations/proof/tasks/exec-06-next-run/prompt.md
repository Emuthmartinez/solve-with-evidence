Write `solution.py` with one function:

```python
from datetime import datetime

def next_run(expr: str, after: datetime) -> datetime | None:
```

`expr` is a schedule of five fields, in this order:

| Field | Allowed values |
|---|---|
| minute | 0 to 59 |
| hour | 0 to 23 |
| day of month | 1 to 31 |
| month | 1 to 12 |
| day of week | 0 to 7. 0 and 7 both mean Sunday, 1 is Monday, 2 Tuesday, and so on to 6, Saturday |

`next_run` returns the earliest minute strictly after `after` that the schedule matches.

Rules:

1. Fields are separated by one or more whitespace characters. Leading and trailing whitespace is ignored. Any number of fields other than five raises `ValueError`.
2. A field is a comma-separated list of one or more items. The field matches every value that any of its items matches. An item is one of:
   - `*`: every allowed value of the field.
   - `N`: the single value N.
   - `A-B`: every value from A to B, both included.
   - `*/S`: the field's lowest allowed value, then every S-th value after it, up to the highest allowed value. In the day-of-month field, `*/7` is 1, 8, 15, 22, 29.
   - `A-B/S`: A, A+S, A+2S, and so on, not past B. `10-50/15` is 10, 25, 40.
3. N, A, B and S are written with the ASCII digits 0 to 9 only. Raise `ValueError` for any of these:
   - an empty item, as in `1,,2` or `5,`;
   - any other form or character, including names such as `MON`, a sign such as `-1`, and a step after a single value such as `5/15`;
   - a value outside the field's allowed values (this applies to N, A and B);
   - a range whose A is greater than B, such as `5-1`;
   - a step S of 0. A step larger than the range is allowed: `*/100` in the minute field matches only 0.
4. A day-of-month or day-of-week field is unrestricted only when its whole text is exactly `*`. Any other text, including `*/1` and `1-31`, makes that field restricted.
5. A minute matches when its minute, hour and month each match their fields, and its day matches:
   - both day fields restricted: the day matches when its day of month matches or its day of week matches (either one is enough);
   - only one day field restricted: that field must match;
   - neither restricted: every day matches.
6. The result is strictly after `after` and has second 0 and microsecond 0. `after` may have non-zero seconds and microseconds.
7. Datetimes are naive. Ignore time zones and daylight saving time: every day has 24 hours of 60 minutes. Use the Gregorian calendar: a year is a leap year when it is divisible by 4, except years divisible by 100 that are not divisible by 400 (2000 is a leap year, 2100 is not).
8. Only minutes no later than `after + timedelta(days=3000)` count. If no minute in that span matches, return `None`. A schedule that can never match, such as 30 February, returns `None`.
9. Each call returns in well under one second, including calls that return `None`.

Examples:

```python
next_run("30 9 * * 1-5", datetime(2026, 11, 13, 9, 30))  # datetime(2026, 11, 16, 9, 30)
next_run("0 0 13 * 5", datetime(2026, 11, 14))           # datetime(2026, 11, 20, 0, 0)
next_run("0 0 30 2 *", datetime(2026, 1, 1))             # None
```

The first example skips the weekend: 13 November 2026 is a Friday. In the second, both day fields are restricted, so the next Friday (20 November) comes before the next 13th.

Use the Python standard library only.
