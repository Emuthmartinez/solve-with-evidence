"""Price a shopping cart against the catalog."""
from collections import namedtuple

from shop.errors import Discontinued, UnknownProduct

PricedLine = namedtuple('PricedLine', 'sku qty unit_cents total_cents')


def unit_cents(product, qty):
    """The bulk price applies to a line of at least `bulk_qty` units."""
    if product.bulk_qty and qty >= product.bulk_qty:
        return product.bulk_cents
    return product.unit_cents


def price_cart(catalog, lines):
    """Price every line of a cart with one catalog call."""
    lines = list(lines)
    for sku, qty in lines:
        if type(qty) is not int or qty <= 0:
            raise ValueError(f'quantity must be a positive int: {qty!r}')
    products = catalog.get_many(list({sku for sku, _ in lines}))
    for sku, _ in lines:
        if sku not in products:
            raise UnknownProduct(sku)
    priced = []
    for sku, qty in lines:
        product = products[sku]
        if product.discontinued:
            raise Discontinued(sku)
        unit = unit_cents(product, qty)
        priced.append(PricedLine(product.sku, qty, unit, unit * qty))
    return priced
