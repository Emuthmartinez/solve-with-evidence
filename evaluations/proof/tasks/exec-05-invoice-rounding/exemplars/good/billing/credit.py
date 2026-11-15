"""Credit notes: what we give back against an invoice."""
from billing.invoice import build_invoice


def credit_note(lines, credited=None):
    """Compute a credit note against the invoice made of `lines`, a list of billing.invoice.Line.

    With `credited` left as None the whole invoice is credited. A full credit note is the
    exact negative of its invoice, cent for cent: what build_invoice(lines) returns, with
    every amount negated and the same skus, rates and order.

    For a partial credit note, `credited` is a dict that maps the position of a line in
    `lines` (0 for the first line) to the quantity credited on that line. A line whose
    position is not in `credited` is not credited. docs/POLICY.md says how a partial credit
    note is computed.

    Returns a dict of the same shape as build_invoice returns.
    """
    if credited is not None:
        lines = [line._replace(quantity=credited[position])
                 for position, line in enumerate(lines) if position in credited]
    # A credit note has no arithmetic of its own, so it cannot drift from the invoice.
    invoice = build_invoice(lines)
    return {
        'lines': [dict(entry, gross=-entry['gross'], discount=-entry['discount'], net=-entry['net'])
                  for entry in invoice['lines']],
        'taxes': [dict(entry, net=-entry['net'], tax=-entry['tax']) for entry in invoice['taxes']],
        'net': -invoice['net'],
        'tax': -invoice['tax'],
        'total': -invoice['total'],
    }
