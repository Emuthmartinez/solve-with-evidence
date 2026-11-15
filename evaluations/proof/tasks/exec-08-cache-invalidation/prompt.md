`products/` is the product service of a web shop. `REPORT.md` is the support report you are picking up: an edited price still shows the old price.

Fix `products/service.py` so that `products.service.Service` meets every guarantee in `docs/caching.md`, within the costs that page states. The report shows one symptom. `docs/caching.md` is the authority for what the cache must do.

- Keep the public methods of `Service`, what they return and what they raise. Their docstrings state that behavior.
- `products/backend.py` documents the backend's contract. The backend is not yours to change. Your code will run against a backend with that contract, not against your copy of that file.
- Everything else in the package must keep working.
- `python3 test_service.py` runs the existing tests. They pass today and must still pass. They are examples, not the full contract.

Use the Python standard library only. Deliver the change in `products/service.py`.
