Write `solution.py` with one function:

```python
def satisfies(version: str, spec: str) -> bool:
```

It returns whether `version` falls inside the version range `spec`. Follow exactly the rules below, not the behavior of any package manager.

Rules for versions:

1. A version is `MAJOR.MINOR.PATCH`, optionally followed by `-PRERELEASE`, then optionally by `+BUILD`. MAJOR, MINOR and PATCH are decimal numbers written with the digits 0-9 and no leading zero (`0` is valid, `01` is not).
2. PRERELEASE and BUILD are each one or more identifiers separated by `.`. An identifier is a non-empty run of ASCII letters, digits 0-9 and `-`. In PRERELEASE, an identifier made only of digits is numeric and must not have a leading zero (`0` is valid, `01` is not, `0a` is valid because it is not numeric). BUILD identifiers have no leading-zero rule.
3. `version` must be exactly one such string, with no spaces or other characters. Anything else raises `ValueError`.
4. BUILD is ignored by every comparison: `1.2.3+a` and `1.2.3+b` both equal `1.2.3`.

Rules for ordering:

5. Compare MAJOR, then MINOR, then PATCH, as integers.
6. When those are equal, a version with a PRERELEASE is lower than the same version without one: `1.0.0-rc.1 < 1.0.0`.
7. Two PRERELEASEs compare identifier by identifier from the left. Two numeric identifiers compare as integers. A numeric identifier is lower than a non-numeric one. Two non-numeric identifiers compare character by character in ASCII order. When one PRERELEASE runs out of identifiers and all of its identifiers equal the start of the other, the shorter one is lower: `1.0.0-alpha < 1.0.0-alpha.1`.

Rules for partial versions, the operands inside `spec`:

8. A partial version is `X`, `X.Y` or `X.Y.Z`. Each part is a number written as in rule 1, or a wildcard: `x`, `X` or `*`. Once a part is a wildcard, every later part must also be a wildcard (`1.x.3` is invalid). A `-PRERELEASE` and a `+BUILD`, written as in rule 2, may follow only when all three parts are numbers.
9. Let N be the numeric parts of a partial version, from the left, before any wildcard. The partial's *floor* is N padded with zeros to three parts, plus its PRERELEASE if it has one (`1.2` gives `1.2.0`). When N has fewer than three parts, the partial's *ceiling* is N with its last part increased by 1, then padded with zeros (`1.2` gives `1.3.0`; `1` gives `2.0.0`). When N is empty (`*`, `x.x`), the floor is `0.0.0` and there is no ceiling.

Rules for ranges:

10. `spec` is one or more sets separated by `||`. `version` satisfies `spec` when it satisfies at least one set. Spaces at the start and end of `spec` and around `||` are ignored.
11. A set is one or more terms separated by one or more spaces. `version` satisfies a set when it satisfies every term in it. An empty set (an empty `spec`, a `spec` of only spaces, or nothing on one side of a `||`) raises `ValueError`.
12. The terms are listed below. P is a partial version written straight after its operator, with no space in between. "Full" means P has three numeric parts.
    - `P` or `=P`: if P is full, the version equals P. Otherwise floor <= version < ceiling. With N empty, every version passes this term.
    - `>=P`: version >= floor.
    - `>P`: if P is full, version > P. Otherwise version >= ceiling.
    - `<P`: version < floor.
    - `<=P`: if P is full, version <= P. Otherwise version < ceiling.
    - `~P`: floor <= version < U. U is `X.(Y+1).0` when P has a numeric MINOR part, and `(X+1).0.0` when only MAJOR is numeric.
    - `^P`: floor <= version < U. To build U, take N, increase its leftmost non-zero part by 1 and set every part after it to 0. If every part of N is 0, increase the last part of N by 1 instead. Then pad U with zeros to three parts. So `^1.2.3` gives U = `2.0.0`, `^0.2.3` gives `0.3.0`, `^0.0.3` gives `0.0.4`, `^0.0` gives `0.1.0` and `^0` gives `1.0.0`.
    - `A - B`: three tokens in a row, a partial version A with no operator, a token that is exactly `-`, and a partial version B with no operator. It means the same as the two terms `>=A <=B`.
13. In every term except `P` and `=P`, a partial version with N empty raises `ValueError` (for example `>=*`, `^x`, `1.2.3 - *`).
14. Any other term raises `ValueError`. This includes an unknown operator, a space between an operator and its partial version, a `-` token that is not between two partial versions without operators, and an invalid partial version. An invalid term raises even when another set of the same `spec` would already match.
15. Prerelease rule: a version that has a PRERELEASE satisfies a set only when it passes every term of that set and that same set contains a partial version written with a PRERELEASE whose MAJOR, MINOR and PATCH equal the version's. A partial version in a different set does not count. A version without a PRERELEASE only has to pass the terms.

Examples:

```python
satisfies("1.4.0", "^1.2.3 <1.5.0")               # True
satisfies("1.2.4-beta.1", ">=1.2.4-alpha <1.3.0")  # True
satisfies("1.3.0-beta", "^1.2.3")                  # False, by rule 15
```

Use the Python standard library only.
