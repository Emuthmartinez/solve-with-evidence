# BILL-731: invoice INV-20418 is one cent short

Reported by accounts receivable, from a customer's email.

## The customer

> Your invoice INV-20418 comes to 47.17. Our purchasing system computes 47.18 from the same lines, and it will not release the payment until the two agree.
>
> 19 % of 13.50 is 2.565. We round that to 2.57. Your invoice shows 2.56.

## The invoice

| SKU | Quantity | Unit price | Discount | Tax code |
|---|---|---|---|---|
| MUG | 3 | 4.50 | none | STD |
| ATLAS | 2 | 12.00 | 10 % | BOOKS |
| FREIGHT | 1 | 8.00 | none | EXPORT |

| | We billed | The customer computes |
|---|---|---|
| Net total | 43.10 | 43.10 |
| Tax at 19 % | 2.56 | 2.57 |
| Tax at 7 % | 1.51 | 1.51 |
| Tax at 0 % | 0.00 | 0.00 |
| Total | 47.17 | 47.18 |

Finance has checked the customer's figures against `docs/POLICY.md`. The customer is right.

## Triage note

Probably Python's `round()` in `billing/money.py`. It rounds halves to even, so 256.5 cents become 256. Looks like a one-line fix.

Customers have raised other one-cent differences this quarter, on invoices and on credit notes. This is the first report that came with the lines attached.
