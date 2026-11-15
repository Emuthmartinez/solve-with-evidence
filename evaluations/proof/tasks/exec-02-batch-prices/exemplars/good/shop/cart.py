"""Price a shopping cart against the catalog."""
from collections import namedtuple

from shop.errors import Discontinued, UnknownProduct

PricedLine = namedtuple('PricedLine', 'sku qty unit_cents total_cents')


def sellable(product, sku):
    """Return the product, or raise the error that says why it cannot be sold."""
    if product is None:
        raise UnknownProduct(sku)
    if product.discontinued:
        raise Discontinued(sku)
    return product


def resolve(catalog, sku):
    """Fetch one product, or raise the error that says why it cannot be sold."""
    return sellable(catalog.get(sku), sku)


def unit_cents(product, qty):
    """The bulk price applies to a line of at least `bulk_qty` units."""
    if product.bulk_qty and qty >= product.bulk_qty:
        return product.bulk_cents
    return product.unit_cents


def price_cart(catalog, lines):
    """Price every line of a cart.

    `lines` is any iterable of (sku, qty) pairs, such as a list or a generator. It is read once.

    Returns a list with one PricedLine per line, in cart order. `PricedLine.sku` is the
    product's canonical SKU. Two lines for the same product stay two lines, and each is priced
    on its own quantity.

    A quantity that is not a positive int raises ValueError before the catalog is contacted.
    A bool is not an int here. Otherwise the first line, in cart order, that cannot be sold
    decides the error: UnknownProduct when the catalog has no such product, Discontinued when
    the product is discontinued. The exception's `sku` is the SKU as that line wrote it.
    """
    cart = []
    for sku, qty in lines:
        if type(qty) is not int or qty <= 0:
            raise ValueError(f'quantity must be a positive int: {qty!r}')
        cart.append((sku, qty))
    # The service counts 'ab-1' and 'AB-1' as one product and rejects a batch that names it twice.
    wanted = list(dict.fromkeys(sku.upper() for sku, _ in cart))
    products = {}
    for start in range(0, len(wanted), catalog.MAX_BATCH):
        products.update(catalog.get_many(wanted[start:start + catalog.MAX_BATCH]))
    priced = []
    for sku, qty in cart:
        product = sellable(products.get(sku.upper()), sku)
        unit = unit_cents(product, qty)
        priced.append(PricedLine(product.sku, qty, unit, unit * qty))
    return priced
