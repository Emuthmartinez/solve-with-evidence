# exec-05-invoice-rounding: fairness notes

The solver never sees this file, the grader or the exemplars.

## What the task is

Fix a reported one-cent error on an invoice in a small billing package, and make the package follow the finance policy for every invoice and credit note. The report names one cause. The package breaks the policy in six places across three modules.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the rules are prose in `docs/POLICY.md`, with worked examples that cover some cases and not others. The policy defines each amount once. It does not warn about the mistakes below. The issue's guess, `round()` in `money.py`, is correct and fixes the reported invoice by itself. The other five causes stay silent for most invoices:

| Cause | Where | When it shows |
|---|---|---|
| Half a cent is rounded to even | `money.py` | Only on an exact half cent whose lower cent is even. This is the reported one. |
| Percentages go through float | `money.py`, `invoice.py`, `credit.py` | Only on an exact half cent that the float product lands just under. |
| The net is rounded, and the discount is what remains | `invoice.py` | Only when the discount is an exact half cent. |
| Tax is computed line by line and added up | `invoice.py`, `credit.py` | Only when the line fractions add up across a half cent. |
| Tax is grouped by tax code | `invoice.py`, `credit.py` | Only when two codes with the same rate are on one invoice. |
| Credit notes round half a cent up, not away from zero | `credit.py` | Only on an exact half cent of a negative amount. |

`credit.py` repeats the invoice arithmetic with its own rounding, so a fix to `money.py` and `invoice.py` leaves credit notes wrong. The existing tests pass on the starter and on every mistake above. Nothing in the prompt says which rules the package breaks.

## What the bad exemplar does

It takes the issue's guess. `round_cents` becomes `math.floor(value + 0.5)`, and `invoice.py` gains a docstring sentence and a comment. The issue's invoice then totals 47.18 and `test_invoice.py` passes. Tax is still line by line and by code, percentages still go through float, the net is still the rounded figure, negative half cents now round towards zero, and `credit.py` is untouched.

## Hidden checks and the sentence each follows from

All sentences are in `docs/POLICY.md` unless the last column names another file. Every expected total is the sum the Totals section defines: "The net total is the sum of the net amounts of the lines. The tax total is the sum of the taxes in the breakdown. The invoice total is the net total plus the tax total."

| Check | Stated rule | Where |
|---|---|---|
| the invoice in the issue totals 47.18 | "An amount that lies exactly halfway between two cents is rounded away from zero: 2.565 becomes 2.57". The issue gives the lines and the total of 47.18 that finance confirmed | Rounding; `ISSUE.md` |
| half a cent of discount rounds up | "Its discount is the discount percentage of the gross amount, rounded to the cent on that line.", with the halfway rule. 5 % of 2.50 is 0.125 | Amounts and lines; Rounding |
| the discount is rounded and the net is what remains | "Its discount is the discount percentage of the gross amount, rounded to the cent on that line. Its net amount is the gross amount less that discount." 5 % of 0.70 is 0.035, so the discount is 0.04 and the net 0.66 | Amounts and lines; Rounding |
| tax is charged once on the summed nets of a rate | "For each rate, add up the net amounts of all the lines at that rate, whatever their tax codes, take the rate's percentage of that sum, and round once." | Tax |
| two codes with the same rate share one breakdown entry | "Several codes can carry the same rate.", "add up the net amounts of all the lines at that rate, whatever their tax codes" and "The tax breakdown of an invoice has one entry for each rate found on its lines." `FOOD` and `BOOKS` are both '7' | Tax; `billing/rates.py` |
| the breakdown runs from the highest rate to the lowest | "Entries run from the highest rate to the lowest." | Tax |
| a zero rate is listed with zero tax | "A rate stays in the breakdown when its tax is 0.00. The 0 % rate is listed" | Tax |
| a 17.5 percent discount of exactly half a cent | "A percentage is a decimal number: 8.75 % is 875/10000, and 17.5 % is 175/1000." and "An amount that lies exactly halfway between two cents in decimal arithmetic is rounded away from zero, whatever a float computation makes of it." 17.5 % of 13.00 is 2.275 | Rounding |
| tax of exactly half a cent at 8.75 percent | The same two sentences. 8.75 % of 106.00 is 9.275 | Rounding |
| a 25 percent discount of exactly half a cent | "Binary floating point must never decide which way an amount rounds." 25 % of 8.70 is 2.175 | Rounding |
| a return line rounds its discount away from zero | "The gross amount, the discount and the net amount of such a line are then negative, by the same rules as for any other line." and "-2.565 becomes -2.57" | Amounts and lines; Rounding |
| negative tax rounds away from zero | "Negative amounts follow the same rule as positive ones". 19 % of -0.50 is -0.095 | Rounding |
| a return line lowers the taxed sum of its rate | "add up the net amounts of all the lines at that rate", where "A quantity can be negative" | Tax; Amounts and lines |
| a 100 percent discount keeps the line and its rate | "At 100 the net amount is 0.00, and the line stays on the invoice." and "so is a rate whose net amounts add up to 0.00" | Amounts and lines; Tax |
| a larger invoice | Twelve lines under the rules above, with "The invoice total is the net total plus the tax total." No amount on it is half a cent | Amounts and lines; Tax; Totals |
| amounts are ints under the documented keys | "Returns a dict with exactly these keys" and "Every amount is an int, in cents." The prompt says to keep "the shape of what they return" | `build_invoice` docstring; `prompt.md` |
| full credit note of the issue invoice | "It is the exact negative of that invoice, cent for cent and in every figure" | Credit notes |
| full credit note mirrors a half cent discount | The same sentence | Credit notes |
| full credit note mirrors tax on summed nets | The same sentence | Credit notes |
| full credit note mirrors half a cent of tax at 8.75 percent | The same sentence | Credit notes |
| full credit note of the larger invoice | The same sentence, and "Lines and breakdown entries keep the order they have on the invoice." | Credit notes |
| partial credit is the negative of an invoice for the credited quantities | "Take the lines being credited, in the order they have on the invoice, each with its credited quantity in place of its invoiced quantity. Compute the invoice for those lines by the rules above. The credit note is the exact negative of that invoice." | Credit notes |
| partial credit taxes the credited lines together | "Compute the invoice for those lines by the rules above.", so tax is per rate on the credited nets | Credit notes; Tax |
| partial credit lists lines in invoice order | "Take the lines being credited, in the order they have on the invoice". `credited` is "a dict that maps the position of a line in `lines` (0 for the first line) to the quantity credited on that line" | Credit notes; `credit_note` docstring |
| partial credit leaves out what is not credited | "A line that is not credited is not on the credit note, and a rate found only on such lines is not in its breakdown." | Credit notes |

The grader builds every line with `billing.invoice.Line` and calls `build_invoice(lines)`, `credit_note(lines)` and `credit_note(lines, credited)`, as the docstrings and `test_invoice.py` do. It compares whole results, so a result with other keys fails. `test_invoice.py` already shows the result shape, a 0 % entry, int amounts, a negative quantity and a partial credit note that leaves a line out.

The three float checks use invoices found by brute force. `1300 * (17.5 / 100)` is 227.49999999999997 and `10600 * (8.75 / 100)` is 927.4999999999999, where the starter's `percent_of` multiplies by `float(percent) / 100`. `870 / 100 * 25` is 217.49999999999997, for a fix that divides the cents first. For amounts up to 2,000.00, the rates 19 and 7 never round wrongly in the starter's float form, which is why `rates.py` carries 8.75. All three values are the same on Python 3.9 and 3.15.

A solution is not required to use any particular arithmetic. When the task was written, five other correct solutions passed every check: `Decimal` with `ROUND_HALF_UP`, integer arithmetic on scaled percentages, float with an epsilon and symmetric rounding, a credit note with exact arithmetic of its own, and a credit note computed on negated quantities.

`variants/exec-05-invoice-rounding.py` holds one plausible mistake per rule. `test_bench.py` checks that each fails exactly the checks it lists.
