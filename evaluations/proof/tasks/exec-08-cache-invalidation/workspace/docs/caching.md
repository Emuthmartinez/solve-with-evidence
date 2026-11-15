# Product service caching

`products.service.Service` keeps a read-through cache in front of the backend. A backend call takes about 40 ms, and the shop reads products far more often than it writes them. This page states what the cache guarantees and what it may cost. The service and its tests follow it.

The service is the only writer to the backend. No cache entry can go stale on its own, so entries never expire. Only the service's own writes make entries wrong.

## What the cache holds

- A product entry for each product id the service has looked up. It holds the product the backend returned, or a not-found entry when `get` returned None.
- A listing entry for each category the service has listed. It holds the ids that `ids_in_category` returned.

## What a read costs

Costs are counted in backend calls. The order of the calls inside one read does not matter.

- `get_product(id)` makes exactly one call, `get(id)`, when there is no product entry for `id`, and stores the product entry. A missing product gets a not-found entry. When there is a product entry, `get_product` makes no call.
- `list_category(category)` makes one `ids_in_category(category)` call when there is no listing entry for `category`, and stores the listing entry. Then it makes one `get(id)` call for each listed id that has no product entry, and stores that product entry. It makes no other call.

So repeating a read, with no write in between, makes no call.

## Guarantees

1. **Read your writes.** Once `create_product`, `update_product`, `delete_product` or `reprice_category` returns or raises, every read reflects every write the backend accepted.

2. **What a write costs.** Each of `create_product`, `update_product` and `delete_product` first looks up the product it writes the same way `get_product` does: no call when there is a product entry (a not-found entry counts), otherwise one `get`. When the write goes ahead, it then makes exactly one `put` (create, update) or one `delete` (delete). When the method raises KeyError or ValueError, it makes no `put` or `delete` call. `reprice_category` reads the listing the same way `list_category` does, then makes one `put` per product, in id order. It makes no other call, and no call after the first `put` the backend rejects.

3. **A write uncaches only what it can affect.** A write may make later reads cost backend calls only for the product it wrote, and for the listing of that product's category. When an update moves a product to another category, both listings count: the category it had before and the one it has after. Every other product entry and listing entry stays cached, and reading it after the write makes no call. A read of an affected entry costs at most what it costs with no entry. For example, listing the written product's category again may call `ids_in_category` for that category and `get` for the written product, but never `get` for another product.

4. **Not-found is cached too.** Asking again for a missing id makes no call. Once `create_product` adds a product with that id, `get_product` returns it.

5. **A failed write changes nothing.** When the backend rejects a write with BackendError, the method raises that error. When `create_product`, `update_product` or `delete_product` raises, whether with BackendError, KeyError or ValueError, every entry that was cached before the call is still cached afterwards, and every read returns what it returned before the call. Guarantee 7 covers `reprice_category`.

6. **Results are the caller's own copies.** Changing a dict or list that `get_product` or `list_category` returned never changes what a later read returns. Neither does changing a dict after passing it to `create_product` or `update_product`.

7. **A method that writes several times is a series of writes.** `reprice_category` writes one product at a time. When the backend rejects one, guarantees 1, 3 and 5 hold for each write separately. The products written before the rejected one read back their new price. The rejected product stays cached as it was, and reading it makes no call.

## Results and errors

The docstrings in `products/service.py` state what each method returns and raises. A change to the cache keeps them.

## Not acceptable

Dropping the whole cache on a write. The nightly import writes a few thousand products, and the shop's pages read the rest of the catalog in between. Dropping everything on each write would send every one of those reads back to the backend. Guarantee 3 rules it out.
