Write `solution.py` with one function:

```python
def allocate(total_cents: int, weights: list[int]) -> list[int]:
```

It splits an amount of money, in whole cents, across entries in proportion to their weights.

Rules:

1. The result has one integer per weight and sums to exactly `total_cents`.
2. A negative weight raises `ValueError`. An empty `weights` list returns `[]` when `total_cents` is 0 and raises `ValueError` otherwise.
3. If every weight is 0, treat every weight as 1.
4. For a non-negative total, each entry first gets the floor of its exact share, `total_cents * weight / sum(weights)`.
5. The cents left over are handed out one each, to the entries with the largest fractional part of their exact share. Break ties by larger weight, then by earlier position.
6. An entry whose weight is 0 never gets a cent, except under rule 3.
7. A negative total is a refund: `allocate(-t, w)` equals `allocate(t, w)` with every value negated.

Amounts can be large. `total_cents` up to 10**30 must stay exact.

Examples:

```python
allocate(100, [1, 1, 1])   # [34, 33, 33]
allocate(10, [3, 0, 7])    # [3, 0, 7]
allocate(-100, [1, 1, 1])  # [-34, -33, -33]
```

Use the Python standard library only.
