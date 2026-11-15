`shop/` prices carts for a web shop. `TICKET.md` is the performance ticket you are picking up: `shop.cart.price_cart` makes one catalog round trip per cart line.

Change `shop/cart.py` so that `price_cart` stays within the round-trip budget in `TICKET.md`.

- `price_cart` must return and raise exactly what it does today, for every cart. Its docstring states that behavior.
- `shop/catalog.py` documents the catalog service's contract. The service is not yours to change. Your code will run against a client with that contract, not against your copy of that file.
- Nothing else in the package may change behavior.
- `python3 test_cart.py` runs the existing tests. They pass today and must still pass. They are examples, not the full contract.

Use the Python standard library only. Deliver the change in `shop/cart.py`.
