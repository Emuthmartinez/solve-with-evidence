# SHOP-482: cart pricing makes one catalog call per line

Reported by the checkout on-call.

A wholesale reorder of 400 lines took 33 seconds to price. `price_cart` calls `Catalog.get` once per line, and each call is a round trip of about 80 ms. Large carts repeat products: the same item ships on several delivery dates, one line per date.

## Wanted

`price_cart` fetches products with `Catalog.get_many`.

The budget, for a cart that names D different products:

- no `get` call;
- at most ceil(D / `Catalog.MAX_BATCH`) `get_many` calls;
- no call at all when the cart is empty or a quantity is invalid.

The budget holds whether the cart prices or raises.

## Not wanted

- No cache that outlives one call to `price_cart`. Prices change during the day.
- No change to what `price_cart` returns or raises.
