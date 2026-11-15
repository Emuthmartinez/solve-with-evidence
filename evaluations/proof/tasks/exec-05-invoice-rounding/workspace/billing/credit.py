"""Credit notes: what we give back against an invoice."""
import math

from billing.rates import rate_for


def _half_up(value):
    # BILL-388: credit notes round halves up, not to even.
    return math.floor(value + 0.5)


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
    out = []
    groups = {}
    for position, line in enumerate(lines):
        if credited is None:
            quantity = line.quantity
        elif position in credited:
            quantity = credited[position]
        else:
            continue
        rate = rate_for(line.tax_code)
        gross = -quantity * line.unit_cents
        discount = _half_up(gross * (float(line.discount_percent) / 100))
        net = gross - discount
        out.append({'sku': line.sku, 'gross': gross, 'discount': discount, 'net': net, 'rate': rate})
        group = groups.setdefault(line.tax_code, {'rate': rate, 'net': 0, 'tax': 0})
        group['net'] += net
        group['tax'] += _half_up(net * (float(rate) / 100))
    taxes = sorted(groups.values(), key=lambda group: float(group['rate']), reverse=True)
    net = sum(entry['net'] for entry in out)
    tax = sum(group['tax'] for group in taxes)
    return {'lines': out, 'taxes': taxes, 'net': net, 'tax': tax, 'total': net + tax}
