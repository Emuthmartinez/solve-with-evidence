# feed

| File | What it does |
|---|---|
| `feed/store.py` | The post store. The in-memory class has the service store's contract and is what tests use. |
| `feed/pager.py` | `page` returns one page of the home feed. |
| `feed/api.py` | `get_feed` serves `GET /feed` to the mobile apps. |
| `feed/export.py` | `export_all` copies the whole feed to the data warehouse every night. |
| `docs/api.md` | The paging contract. |

Run the tests with `python3 test_feed.py`.
