"""Plausible mistakes for exec-02-batch-prices. Each is the good exemplar with one edit."""
CART = 'shop/cart.py'
DEDUPE = "    wanted = list(dict.fromkeys(sku.upper() for sku, _ in cart))\n"
FETCH = ("    for start in range(0, len(wanted), catalog.MAX_BATCH):\n"
         "        products.update(catalog.get_many(wanted[start:start + catalog.MAX_BATCH]))\n")
LOOKUP = "        product = sellable(products.get(sku.upper()), sku)\n"
BIG = ['51 products take two batches', '400 lines of 120 products take three batches',
       'first unsellable line wins across batches', 'budget holds when the cart raises']

VARIANTS = [
    ('one batch for the whole cart, however large',
     {CART: [(FETCH, "    if wanted:\n        products.update(catalog.get_many(wanted))\n")]}, BIG),
    ('products deduplicated by the SKU as written, not by product',
     {CART: [(DEDUPE, "    wanted = list(dict.fromkeys(sku for sku, _ in cart))\n")]},
     ['one product in several letter cases is one product', 'letter case does not inflate the batch count']),
    ('every line sent to the service, repeats included',
     {CART: [(DEDUPE, "    wanted = [sku.upper() for sku, _ in cart]\n")]},
     ['a repeated product is requested once', 'one product in several letter cases is one product',
      'letter case does not inflate the batch count', '400 lines of 120 products take three batches',
      'budget holds when the cart raises', 'bulk price is per line']),
    ('unknown products reported before discontinued ones',
     {CART: [("    priced = []\n    for sku, qty in cart:\n",
              "    for sku, _ in cart:\n        if sku.upper() not in products:\n            raise UnknownProduct(sku)\n"
              "    priced = []\n    for sku, qty in cart:\n")]},
     ['discontinued line before unknown line']),
    ('batches sent in SKU order and each checked as it arrives',
     {CART: [(DEDUPE, "    wanted = sorted({sku.upper() for sku, _ in cart})\n"),
             (FETCH, "    for start in range(0, len(wanted), catalog.MAX_BATCH):\n"
                     "        batch = wanted[start:start + catalog.MAX_BATCH]\n"
                     "        found = catalog.get_many(batch)\n"
                     "        for sku, _ in cart:\n"
                     "            if sku.upper() in batch:\n"
                     "                sellable(found.get(sku.upper()), sku)\n"
                     "        products.update(found)\n")]},
     ['first unsellable line wins across batches']),
    ('discontinued products reported before unknown ones',
     {CART: [("    priced = []\n    for sku, qty in cart:\n",
              "    for sku, _ in cart:\n        if sku.upper() in products and products[sku.upper()].discontinued:\n"
              "            raise Discontinued(sku)\n    priced = []\n    for sku, qty in cart:\n")]},
     ['unknown line before discontinued line', 'first unsellable line wins across batches']),
    ('the cart is read twice',
     {CART: [("    cart = []\n    for sku, qty in lines:\n", "    cart = lines\n    for sku, qty in lines:\n"),
             ("        cart.append((sku, qty))\n", "")]},
     ['lines may be a generator']),
    ('products remembered between carts',
     {CART: [("def price_cart(catalog, lines):", "SEEN = {}\n\n\ndef price_cart(catalog, lines):"),
             ("    products = {}\n", "    products = SEEN\n    wanted = [sku for sku in wanted if sku not in SEEN]\n")]},
     ['no cache between carts', '51 products take two batches', '400 lines of 120 products take three batches',
      'a repeated product is requested once', 'one product in several letter cases is one product',
      'letter case does not inflate the batch count']),
    ('resolve now takes the fetched products',
     {CART: [("def resolve(catalog, sku):", "def resolve(products, sku):"),
             ("    return sellable(catalog.get(sku), sku)", "    return sellable(products.get(sku.upper()), sku)"),
             (LOOKUP, "        product = resolve(products, sku)\n")]},
     ['quote_line still works']),
    ('the line keeps the SKU as written',
     {CART: [("PricedLine(product.sku, qty", "PricedLine(sku, qty")]},
     ['result carries the canonical SKU', 'one product in several letter cases is one product',
      'letter case does not inflate the batch count']),
    ('the error carries the canonical SKU',
     {CART: [(LOOKUP, "        product = sellable(products.get(sku.upper()), sku.upper())\n")]},
     ['error carries the SKU as written']),
    ('repeated lines priced on their combined quantity',
     {CART: [("        unit = unit_cents(product, qty)\n",
              "        unit = unit_cents(product, sum(q for other, q in cart if other.upper() == sku.upper()))\n")]},
     ['bulk price is per line', 'one product in several letter cases is one product']),
    ('an empty cart still asks the service',
     {CART: [(FETCH, "    for start in range(0, max(len(wanted), 1), catalog.MAX_BATCH):\n"
                     "        products.update(catalog.get_many(wanted[start:start + catalog.MAX_BATCH]))\n")]},
     ['empty cart makes no call']),
    ('quantities checked while pricing, after the fetch',
     {CART: [("        if type(qty) is not int or qty <= 0:\n            raise ValueError(f'quantity must be a positive int: {qty!r}')\n"
              "        cart.append((sku, qty))\n", "        cart.append((sku, qty))\n"),
             ("        product = sellable(", "        if type(qty) is not int or qty <= 0:\n"
              "            raise ValueError(f'quantity must be a positive int: {qty!r}')\n        product = sellable(")]},
     ['invalid quantity raises before any call']),
    ('a miss in the batch is retried with get',
     {CART: [(LOOKUP, "        product = sellable(products.get(sku.upper()) or catalog.get(sku), sku)\n")]},
     ['budget holds when the cart raises']),
    ('batches of 49',
     {CART: [("catalog.MAX_BATCH", "(catalog.MAX_BATCH - 1)")]},
     ['50 products fit one batch', 'letter case does not inflate the batch count']),
    ('one get_many per line',
     {CART: [(FETCH, "    for sku in wanted:\n        products.update(catalog.get_many([sku]))\n")]},
     ['small cart prices in one batch', '50 products fit one batch', '51 products take two batches',
      '400 lines of 120 products take three batches', 'a repeated product is requested once',
      'letter case does not inflate the batch count', 'budget holds when the cart raises']),
]
