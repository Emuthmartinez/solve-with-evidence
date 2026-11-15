# exec-02-batch-prices: fairness notes

The solver never sees this file, the grader or the exemplars.

## What the task is

Replace one catalog round trip per cart line with batched calls, inside an existing package, without changing what `price_cart` returns or raises.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the rules sit in four places the solver has to read: the ticket, the `price_cart` docstring, the `get_many` docstring and `quote.py`. The existing tests cover a three-line cart and pass for every mistake below. Nothing in the prompt says which rules a batched version is likely to break.

## What the bad exemplar does

It is the first version a quick solver writes: one `get_many` for the set of SKUs as written, unknown products reported first, and the now unused `resolve` helper deleted. It passes `test_cart.py`.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| small cart prices in one batch | "no `get` call; at most ceil(D / `Catalog.MAX_BATCH`) `get_many` calls" | `TICKET.md`, Wanted |
| bulk price is per line | "Two lines for the same product stay two lines, and each is priced on its own quantity." | `price_cart` docstring |
| result carries the canonical SKU | "`PricedLine.sku` is the product's canonical SKU." | `price_cart` docstring |
| error carries the SKU as written | "The exception's `sku` is the SKU as that line wrote it." | `price_cart` docstring |
| 50 products fit one batch | "at most ceil(D / `Catalog.MAX_BATCH`) `get_many` calls", with `MAX_BATCH = 50` | `TICKET.md`; `shop/catalog.py` |
| 51 products take two batches | "A request is malformed when `skus` ... holds more than MAX_BATCH SKUs" | `get_many` docstring |
| 400 lines of 120 products take three batches | The ticket's own cart: 400 lines, repeated products, budget ceil(120 / 50) = 3 | `TICKET.md` |
| a repeated product is requested once | "for a cart that names D different products", and a request is malformed when it "names the same product twice" | `TICKET.md`; `get_many` docstring |
| one product in several letter cases is one product | "SKUs are ASCII and case-insensitive"; malformed when it "names the same product twice, in any letter case" | `get` and `get_many` docstrings |
| letter case does not inflate the batch count | The same two sentences, with the budget counting different products | `TICKET.md`; `shop/catalog.py` |
| empty cart makes no call | "no call at all when the cart is empty or a quantity is invalid" | `TICKET.md` |
| invalid quantity raises before any call | "A quantity that is not a positive int raises ValueError before the catalog is contacted. A bool is not an int here." | `price_cart` docstring |
| discontinued line before unknown line | "the first line, in cart order, that cannot be sold decides the error" | `price_cart` docstring |
| unknown line before discontinued line | The same sentence | `price_cart` docstring |
| first unsellable line wins across batches | The same sentence. Cart order decides, not the order batches come back in | `price_cart` docstring |
| budget holds when the cart raises | "The budget holds whether the cart prices or raises." | `TICKET.md` |
| lines may be a generator | "`lines` is any iterable of (sku, qty) pairs, such as a list or a generator. It is read once." | `price_cart` docstring |
| no cache between carts | "No cache that outlives one call to `price_cart`." | `TICKET.md`, Not wanted |
| quote_line still works | "Nothing else in the package may change behavior." `quote.py` imports `resolve` from `cart.py` | `prompt.md`; `shop/quote.py`; `README.md` |

The grader's catalog is the workspace's `Catalog` class, copied line for line, so a solver who exercises their code against the workspace class sees every rejection the grader can produce.

`variants/exec-02-batch-prices.py` holds one plausible mistake per rule. `test_bench.py` checks that each fails exactly the checks it lists.
