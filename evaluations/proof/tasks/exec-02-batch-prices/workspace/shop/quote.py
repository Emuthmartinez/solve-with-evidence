"""Price one line for the product page."""
from shop.cart import PricedLine, resolve, unit_cents


def quote_line(catalog, sku, qty):
    """Return the PricedLine for `qty` units of `sku`, with one catalog round trip.

    Raises what `price_cart` raises for a cart of that one line.
    """
    if type(qty) is not int or qty <= 0:
        raise ValueError(f'quantity must be a positive int: {qty!r}')
    product = resolve(catalog, sku)
    unit = unit_cents(product, qty)
    return PricedLine(product.sku, qty, unit, unit * qty)
