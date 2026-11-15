`feed/` serves the home feed of a social app. `BUG.md` is the bug you are picking up: while a user scrolls, a new post arrives and page 2 repeats a post from page 1.

Fix it in `feed/pager.py`.

- `docs/api.md` is the paging contract. The report shows one symptom. When you are done, `feed.pager.page` must follow the whole contract.
- Keep the signature of `page` and the shape of `Page`.
- `feed/store.py` documents the store. It is not yours to change. Your pager will run against a store with that contract, not against your copy of that file.
- Nothing else in the package may change behavior. `feed/api.py` and `feed/export.py` call `page` and must keep working.
- `python3 test_feed.py` runs the existing tests. They pass today and must still pass. They are examples, not the full contract.
- Also deliver `test_regression.py` in this directory, run as `python3 test_regression.py` from here. Exit status 0 means it passed. It must fail on the code as shipped today and pass on your fix. It must also pass on any pager that follows `docs/api.md`, so it must not depend on what a cursor looks like. It must be deterministic and finish in a few seconds. A run is stopped after 30 seconds.

Use the Python standard library only. Deliver `feed/pager.py` and `test_regression.py`.
