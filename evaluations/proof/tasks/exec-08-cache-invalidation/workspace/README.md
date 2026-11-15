# products

| File | What it does |
|---|---|
| `products/backend.py` | The product database. The in-memory class has the database's contract and is what tests use. |
| `products/service.py` | `Service` reads and writes products through a cache. Pages and admin screens call it. |
| `products/pricelist.py` | `price_list` builds the printed price list of one category. |
| `docs/caching.md` | What the service's cache guarantees and what it may cost. |

Run the tests with `python3 test_service.py`.
