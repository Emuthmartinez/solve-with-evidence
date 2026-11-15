# SUP-2214: an edited price still shows the old price

Reported by the catalog team, through support.

We raised the price of the Kettle (A1) from 25.00 to 27.00 in the admin screen. The admin screen saved it, and the database holds 27.00. The product page still shows 25.00, and so does the kitchen price list. Only a restart of the product service shows 27.00.

What the admin screen and the product page do, in order:

```python
service.get_product('A1')                             # product page: price_cents 2500
service.update_product('A1', {'price_cents': 2700})   # admin screen saves the new price
service.get_product('A1')                             # product page: still price_cents 2500
```

Suggestion from the reporter: clear the cache on every write. It is the simplest fix, and writes are rare.
