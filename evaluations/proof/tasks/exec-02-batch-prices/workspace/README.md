# shop

| File | What it does |
|---|---|
| `shop/catalog.py` | Client for the catalog service. The in-memory class has the service's contract and is what tests use. |
| `shop/cart.py` | `price_cart` prices a whole cart at checkout. |
| `shop/quote.py` | `quote_line` prices one line for the product page: one product, one round trip. |
| `shop/errors.py` | The errors a cart or a quote can raise. |

Run the tests with `python3 test_cart.py`.
