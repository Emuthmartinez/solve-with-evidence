Your working directory holds three files:

- `solution.py` is an existing stock-ledger module with one class, `Inventory`.
- `SPEC.md` states the rules that `Inventory` must follow.
- `test_visible.py` has one test, which currently fails. Run it with `python3 test_visible.py`.

Rules:

1. Change `solution.py` so that `Inventory` conforms to every numbered statement in `SPEC.md`.
2. `test_visible.py` is one example of a SPEC.md statement. It is not the full specification. Code that passes it can still break other statements.
3. Keep the public names: the class `Inventory` and its methods `restock`, `available`, `reserve`, `reservation`, `release`, `ship` and `snapshot`, with the same parameters.
4. When SPEC.md says a call raises an exception, raise that exact type (`ValueError` or `KeyError`). Hidden tests check the type, not the message.
5. Deliver the fixed module as `solution.py`.

Example of correct behavior:

```python
inventory = Inventory()
inventory.restock("apple", 5)
inventory.restock("apple", 3)
inventory.available("apple")  # 8
```

Use the Python standard library only.
