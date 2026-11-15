# exec-08-cache-invalidation: fairness notes

The solver never sees this file, the grader or the exemplars.

## What the task is

Fix a reported stale read in a product service's read-through cache, and make the cache keep every guarantee in `docs/caching.md` within the backend-call budget that page states, without changing what the service's methods return or raise.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the report shows one symptom: an update does not drop the cached product. The starter breaks the documented guarantees in five more independent ways. Listings are never dropped on a create, a delete or a move. A create leaves the cached not-found entry its own existence check stored. Reads hand out the cached dicts, so `pricelist.py`, which edits the dicts it gets, corrupts the cache. An update drops a listing before the `put`, so a rejected update evicts it. A reprice that fails halfway drops nothing, so the products it already wrote read stale. The reporter suggests clearing the cache on every write. That fixes the report and passes the visible tests, and guarantee 3 rules it out. The rules sit in four places: `docs/caching.md`, the `Service` docstrings, the `Backend` docstrings and `pricelist.py`. The visible tests pass on the starter. Nothing in the prompt says which guarantees the starter breaks.

## What the bad exemplar does

It takes the reporter's suggestion. Every write clears both caches where the starter dropped its one listing, before the backend write. The reprice clears them after its loop. It returns cached dicts, as the starter does. It removes the reported symptom and passes `test_service.py`.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| a product is fetched once | "`get_product(id)` makes exactly one call, `get(id)`, when there is no product entry ... When there is a product entry, `get_product` makes no call." | `docs/caching.md`, What a read costs |
| a missing product is fetched once | "A missing product gets a not-found entry"; "Asking again for a missing id makes no call." | `docs/caching.md`, What a read costs; guarantee 4 |
| a first listing fetches only uncached products | "one `get(id)` call for each listed id that has no product entry ... It makes no other call." | `docs/caching.md`, What a read costs |
| a repeated listing makes no call | "So repeating a read, with no write in between, makes no call." `list_category`: "A category with no products gives []." | `docs/caching.md`; `list_category` docstring |
| an edited price is read back | "Once `create_product`, `update_product`, `delete_product` or `reprice_category` returns or raises, every read reflects every write the backend accepted." The report's own steps | `docs/caching.md`, guarantee 1; `REPORT.md` |
| an edited price shows in the listing | The same sentence. The report: "so does the kitchen price list" | guarantee 1; `REPORT.md` |
| an edit refetches only the edited product | "listing the written product's category again may call `ids_in_category` for that category and `get` for the written product, but never `get` for another product"; "Every other product entry and listing entry stays cached" | guarantee 3 |
| a write looks its product up through the cache | "first looks up the product it writes the same way `get_product` does: no call when there is a product entry (a not-found entry counts), otherwise one `get`. When the write goes ahead, it then makes exactly one `put` ... or one `delete`" | guarantee 2 |
| a created product shows in the listing | Guarantee 1 | guarantee 1 |
| a created product replaces a cached not-found | "Once `create_product` adds a product with that id, `get_product` returns it." | guarantee 4 |
| a create refetches only what it added | "only for the product it wrote, and for the listing of that product's category" | guarantee 3 |
| a deleted product leaves the listing | Guarantee 1 | guarantee 1 |
| a deleted product reads as missing | Guarantee 1, with `get_product`: "or None when there is no such product" | guarantee 1; `get_product` docstring |
| a delete refetches only its listing | Guarantee 3. Only the listing counts: the deleted product is not read | guarantee 3 |
| a moved product leaves its old listing | "When an update moves a product to another category, both listings count: the category it had before and the one it has after." With guarantee 1 | guarantees 1 and 3 |
| a moved product joins its new listing | The same sentences | guarantees 1 and 3 |
| a move refetches only the two listings | The same sentence, and "Every other product entry and listing entry stays cached" | guarantee 3 |
| a rejected update raises the backend error | "When the backend rejects a write with BackendError, the method raises that error." `update_product` raises "the backend's BackendError when the backend rejects the changed product" | guarantee 5; `update_product` docstring |
| a rejected update keeps the cache | "every entry that was cached before the call is still cached afterwards, and every read returns what it returned before the call" | guarantee 5 |
| a rejected create keeps the cache | The same sentence | guarantee 5 |
| missing product errors change nothing | Guarantee 5 names KeyError and ValueError. "When the method raises KeyError or ValueError, it makes no `put` or `delete` call." The docstrings name KeyError for a missing product and ValueError for an existing id | guarantees 2 and 5; `Service` docstrings |
| changing a returned product changes no later read | "Changing a dict or list that `get_product` or `list_category` returned never changes what a later read returns." | guarantee 6; `get_product` docstring |
| changing a returned listing changes no later read | The same sentence | guarantee 6; `list_category` docstring |
| changing a written dict changes no later read | "Neither does changing a dict after passing it to `create_product` or `update_product`." | guarantee 6 |
| the price list still works | "Everything else in the package must keep working." | `prompt.md`; `products/pricelist.py` |
| the price list leaves the cache intact | `price_list` edits the dicts `list_category` returns, which "are the caller's own: the caller may change them" | guarantee 6; `list_category` docstring; `products/pricelist.py` |
| a whole reprice reads back | "A product's new price is price_cents * (100 + percent) // 100." With guarantee 1 | `reprice_category` docstring; guarantee 1 |
| a partial reprice reads back what was written | "the products written before it keep their new price, and that product and the ones after it keep their old price"; "The products written before the rejected one read back their new price." The Chandelier's new price is over `MAX_PRICE_CENTS` | `reprice_category` docstring; guarantee 7; `products/backend.py` |
| a partial reprice refetches only what it wrote | "then makes one `put` per product, in id order. It makes no other call"; "The rejected product stays cached as it was, and reading it makes no call." | guarantees 2, 3 and 7 |

Each budget check asserts an exact call list only where `docs/caching.md` fixes the cost: a first read, a repeated read, and a write's own calls. After a write, the guarantees only bound what a read of an affected entry may cost. Those checks accept any subset of the allowed calls with no call repeated. A service that refreshes an entry with what it wrote, instead of dropping it, passes them.

The grader's backend is the workspace's `Backend` class, copied line for line. It raises the workspace's own `BackendError` class, so a service that catches that error by name catches the grader's. A solver who exercises the service against the workspace class sees every rejection the grader can produce.

`variants/exec-08-cache-invalidation.py` holds one plausible mistake per rule. `test_bench.py` checks that each fails exactly the checks it lists.
