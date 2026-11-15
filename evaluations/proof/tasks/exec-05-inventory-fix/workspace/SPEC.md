# Stock ledger rules

The `Inventory` class in `solution.py` tracks stock per SKU and the units each order has set aside.

1. A new `Inventory()` knows no SKUs, and its `snapshot()` is `{}`.
2. Every `qty` argument must be an `int` greater than 0. Any other value raises `ValueError`, and the call changes nothing.
3. `restock(sku, qty)` adds `qty` to the SKU's on-hand count. A SKU restocked for the first time starts at 0 on hand and 0 reserved before the addition.
4. `available(sku)` returns on hand minus reserved. An unknown SKU raises `KeyError`.
5. `reserve(order_id, sku, qty)` sets aside `qty` units of the SKU for the order. An unknown SKU raises `KeyError`. If `qty` is more than `available(sku)`, it raises `ValueError` and changes nothing. Reserving again for the same order and SKU adds to that order's reservation.
6. `reservation(order_id, sku)` returns the units the order holds for the SKU, or 0 when it holds none.
7. `release(order_id, sku)` cancels the order's whole reservation for the SKU and returns the number of units released. If the order holds no reservation for the SKU, it raises `KeyError`.
8. `ship(order_id, sku, qty)` sends `qty` reserved units. It lowers both the order's reservation and the SKU's on-hand count by `qty`. If the order holds no reservation for the SKU, it raises `KeyError`. If `qty` is more than the order's reservation, it raises `ValueError` and changes nothing. A reservation that reaches 0 is removed, so a later `release` of it raises `KeyError`.
9. `snapshot()` returns a dict that maps each known SKU to `{"on_hand": int, "reserved": int, "available": int}`, with keys in ascending SKU order. Changing the returned dict, or any dict inside it, never changes the inventory.
