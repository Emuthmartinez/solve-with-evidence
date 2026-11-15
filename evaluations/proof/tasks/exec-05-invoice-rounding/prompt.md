`billing/` computes invoices and credit notes in integer cents. `ISSUE.md` is a report of an invoice that is one cent off, with a guess at the cause.

Fix it. `docs/POLICY.md` is finance's rule book for every amount, and the issue is one symptom. Make `billing` follow the policy for every invoice and every credit note.

- `billing.invoice.Line`, `billing.invoice.build_invoice` and `billing.credit.credit_note` keep their names, their arguments and the shape of what they return. The docstrings state that shape.
- The tax codes and rates in `billing/rates.py` are finance's and stay as they are.
- `python3 test_invoice.py` runs the existing tests. They pass today and must still pass. They are examples, not the full policy.

Use the Python standard library only. Deliver the change in `billing/invoice.py`. Other files in the package may change too.
