"""The printed price list for one category, used by the shop's nightly print job."""


def price_list(service, category):
    """Return one line per product in `category`, in id order: the name, then the price as 25.00."""
    products = service.list_category(category)
    for product in products:
        product['price'] = '%d.%02d' % divmod(product.pop('price_cents'), 100)
    return ['%s %s' % (product['name'], product['price']) for product in products]
