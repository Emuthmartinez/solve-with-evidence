"""Plausible mistakes for exec-08-cache-invalidation. Each is the good exemplar with one edit."""
SERVICE = 'products/service.py'
LOOKUP = ("        if product_id not in self._products:\n"
          "            self._products[product_id] = self.backend.get(product_id)\n"
          "        return self._products[product_id]\n")
GET = "        product = self._lookup(product_id)\n        return None if product is None else dict(product)\n"
LIST = "        return [dict(self._lookup(product_id)) for product_id in self._listings[category]]\n"
CREATE = "        self.backend.put(product)\n        self._forget(product['id'], product['category'])\n"
UPDATE_LOOKUP = "        current = self._lookup(product_id)\n        if current is None:\n            raise KeyError(product_id)\n        product = dict(current)\n"
UPDATE = "        self.backend.put(product)\n        self._forget(product_id, current['category'], product['category'])\n"
DELETE = "        self.backend.delete(product_id)\n        self._forget(product_id, current['category'])\n"
REPRICE = ("        for product in self.list_category(category):\n"
           "            self.update_product(product['id'], {'price_cents': product['price_cents'] * (100 + percent) // 100})\n")

VARIANTS = [
    ('the update leaves the product entry, as the report shows',
     {SERVICE: [(UPDATE, "        self.backend.put(product)\n"
                         "        self._listings.pop(current['category'], None)\n"
                         "        self._listings.pop(product['category'], None)\n")]},
     ['an edited price is read back',
      'an edited price shows in the listing',
      'an edit refetches only the edited product',
      'a moved product joins its new listing',
      'a move refetches only the two listings',
      'changing a written dict changes no later read',
      'a whole reprice reads back',
      'a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
    ('listings are never dropped',
     {SERVICE: [("        for category in categories:\n            self._listings.pop(category, None)\n", "")]},
     ['a created product shows in the listing',
      'a create refetches only what it added',
      'a deleted product leaves the listing',
      'a delete refetches only its listing',
      'a moved product leaves its old listing',
      'a moved product joins its new listing',
      'a move refetches only the two listings']),
    ('an update drops only the new category',
     {SERVICE: [(UPDATE, "        self.backend.put(product)\n        self._forget(product_id, product['category'])\n")]},
     ['a moved product leaves its old listing',
      'a move refetches only the two listings']),
    ('an update drops only the old category',
     {SERVICE: [(UPDATE, "        self.backend.put(product)\n        self._forget(product_id, current['category'])\n")]},
     ['a moved product joins its new listing',
      'a move refetches only the two listings']),
    ('a create drops the listing but keeps the not-found entry',
     {SERVICE: [(CREATE, "        self.backend.put(product)\n        self._listings.pop(product['category'], None)\n")]},
     ['a created product shows in the listing',
      'a created product replaces a cached not-found',
      'a create refetches only what it added',
      'changing a written dict changes no later read']),
    ('a delete keeps the product entry',
     {SERVICE: [(DELETE, "        self.backend.delete(product_id)\n        self._listings.pop(current['category'], None)\n")]},
     ['a deleted product reads as missing']),
    ('an update drops its entries before the put',
     {SERVICE: [(UPDATE, "        self._forget(product_id, current['category'], product['category'])\n"
                         "        self.backend.put(product)\n")]},
     ['a rejected update keeps the cache',
      'a partial reprice refetches only what it wrote']),
    ('a create drops its entries before the put',
     {SERVICE: [(CREATE, "        self._forget(product['id'], product['category'])\n        self.backend.put(product)\n")]},
     ['a rejected create keeps the cache']),
    ('an update merges the changes into the cached dict',
     {SERVICE: [(UPDATE_LOOKUP, "        current = self._lookup(product_id)\n        if current is None:\n"
                                "            raise KeyError(product_id)\n        old_category = current['category']\n"
                                "        product = current\n"),
                (UPDATE, "        self.backend.put(product)\n        self._forget(product_id, old_category, product['category'])\n")]},
     ['a rejected update raises the backend error',
      'a rejected update keeps the cache',
      'a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
    ('a rejected update is swallowed',
     {SERVICE: [(UPDATE, "        try:\n            self.backend.put(product)\n        except Exception:\n            return\n"
                         "        self._forget(product_id, current['category'], product['category'])\n")]},
     ['a rejected update raises the backend error',
      'a rejected update keeps the cache',
      'a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
    ('a write reads the backend instead of the cache',
     {SERVICE: [(UPDATE_LOOKUP, "        current = self.backend.get(product_id)\n        if current is None:\n"
                                "            raise KeyError(product_id)\n        product = dict(current)\n")]},
     ['a write looks its product up through the cache',
      'missing product errors change nothing',
      'a partial reprice refetches only what it wrote']),
    ('a create caches the dict it was given',
     {SERVICE: [(CREATE, "        self.backend.put(product)\n        self._listings.pop(product['category'], None)\n"
                         "        self._products[product['id']] = product\n")]},
     ['changing a written dict changes no later read']),
    ('a create of an existing product writes before it refuses',
     {SERVICE: [("        if self._lookup(product['id']) is not None:\n            raise ValueError('product exists: %s' % product['id'])\n"
                 "        self.backend.put(product)\n",
                 "        existing = self._lookup(product['id'])\n        self.backend.put(product)\n"
                 "        if existing is not None:\n            raise ValueError('product exists: %s' % product['id'])\n")]},
     ['missing product errors change nothing']),
    ('only a cached read returns a copy',
     {SERVICE: [(GET, "        if product_id in self._products:\n            product = self._products[product_id]\n"
                      "            return None if product is None else dict(product)\n"
                      "        return self._lookup(product_id)\n")]},
     ['changing a returned product changes no later read']),
    ('a listing copies the list but not the dicts',
     {SERVICE: [(LIST, "        return [self._lookup(product_id) for product_id in self._listings[category]]\n")]},
     ['changing a returned listing changes no later read',
      'the price list leaves the cache intact']),
    ('a listing returns a generator',
     {SERVICE: [(LIST, "        return (dict(self._lookup(product_id)) for product_id in self._listings[category])\n")]},
     ['a first listing fetches only uncached products',
      'a repeated listing makes no call',
      'an edited price shows in the listing',
      'an edit refetches only the edited product',
      'a write looks its product up through the cache',
      'a created product shows in the listing',
      'a create refetches only what it added',
      'a deleted product leaves the listing',
      'a delete refetches only its listing',
      'a moved product leaves its old listing',
      'a moved product joins its new listing',
      'a move refetches only the two listings',
      'a rejected update keeps the cache',
      'a rejected create keeps the cache',
      'missing product errors change nothing',
      'changing a returned listing changes no later read',
      'the price list still works',
      'the price list leaves the cache intact',
      'a whole reprice reads back',
      'a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
    ('not-found is not cached',
     {SERVICE: [(LOOKUP, "        if product_id in self._products:\n            return self._products[product_id]\n"
                         "        product = self.backend.get(product_id)\n        if product is not None:\n"
                         "            self._products[product_id] = product\n        return product\n")]},
     ['a missing product is fetched once',
      'a write looks its product up through the cache',
      'a delete refetches only its listing',
      'a rejected create keeps the cache',
      'missing product errors change nothing']),
    ('a product read always asks the backend',
     {SERVICE: [(LOOKUP, "        self._products[product_id] = self.backend.get(product_id)\n"
                         "        return self._products[product_id]\n")]},
     ['a product is fetched once',
      'a missing product is fetched once',
      'a first listing fetches only uncached products',
      'a repeated listing makes no call',
      'an edit refetches only the edited product',
      'a write looks its product up through the cache',
      'a create refetches only what it added',
      'a delete refetches only its listing',
      'a move refetches only the two listings',
      'a rejected update keeps the cache',
      'a rejected create keeps the cache',
      'missing product errors change nothing',
      'a partial reprice refetches only what it wrote']),
    ('a listing fetches every product it lists',
     {SERVICE: [(LIST, "        for product_id in self._listings[category]:\n            self._products.pop(product_id, None)\n" + LIST)]},
     ['a first listing fetches only uncached products',
      'a repeated listing makes no call',
      'an edit refetches only the edited product',
      'a create refetches only what it added',
      'a delete refetches only its listing',
      'a move refetches only the two listings',
      'a rejected update keeps the cache',
      'a rejected create keeps the cache',
      'missing product errors change nothing',
      'a partial reprice refetches only what it wrote']),
    ('a listing is not cached',
     {SERVICE: [("        if category not in self._listings:\n            self._listings[category] = ",
                 "        if True:\n            self._listings[category] = ")]},
     ['a repeated listing makes no call',
      'an edit refetches only the edited product',
      'a create refetches only what it added',
      'a delete refetches only its listing',
      'a move refetches only the two listings',
      'a rejected update keeps the cache',
      'a rejected create keeps the cache',
      'missing product errors change nothing',
      'a partial reprice refetches only what it wrote']),
    ('a write drops every product of its category',
     {SERVICE: [("        for category in categories:\n            self._listings.pop(category, None)\n",
                 "        for category in categories:\n            for other in self._listings.pop(category, []):\n"
                 "                self._products.pop(other, None)\n")]},
     ['an edit refetches only the edited product',
      'a create refetches only what it added',
      'a delete refetches only its listing',
      'a move refetches only the two listings',
      'a partial reprice refetches only what it wrote']),
    ('a create drops every listing',
     {SERVICE: [(CREATE, "        self.backend.put(product)\n        self._products.pop(product['id'], None)\n"
                         "        self._listings.clear()\n")]},
     ['a create refetches only what it added']),
    ('a delete drops every listing',
     {SERVICE: [(DELETE, "        self.backend.delete(product_id)\n        self._products.pop(product_id, None)\n"
                         "        self._listings.clear()\n")]},
     ['a delete refetches only its listing']),
    ('a move drops every listing',
     {SERVICE: [(UPDATE, "        self.backend.put(product)\n        self._forget(product_id, current['category'], product['category'])\n"
                         "        if product['category'] != current['category']:\n            self._listings.clear()\n")]},
     ['a move refetches only the two listings']),
    ('a reprice drops its entries only when every write succeeds',
     {SERVICE: [(REPRICE, "        products = self.list_category(category)\n        for product in products:\n"
                          "            self.backend.put(dict(product, price_cents=product['price_cents'] * (100 + percent) // 100))\n"
                          "        for product in products:\n            self._forget(product['id'])\n"
                          "        self._forget('', category)\n")]},
     ['a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
    ('a reprice drops every listed product, written or not',
     {SERVICE: [(REPRICE, "        products = self.list_category(category)\n        try:\n"
                          "            for product in products:\n"
                          "                self.backend.put(dict(product, price_cents=product['price_cents'] * (100 + percent) // 100))\n"
                          "        finally:\n            for product in products:\n                self._forget(product['id'])\n"
                          "            self._forget('', category)\n")]},
     ['a partial reprice refetches only what it wrote']),
    ('a reprice drops only the listing',
     {SERVICE: [(REPRICE, "        products = self.list_category(category)\n        try:\n"
                          "            for product in products:\n"
                          "                self.backend.put(dict(product, price_cents=product['price_cents'] * (100 + percent) // 100))\n"
                          "        finally:\n            self._forget('', category)\n")]},
     ['a whole reprice reads back',
      'a partial reprice reads back what was written',
      'a partial reprice refetches only what it wrote']),
]
