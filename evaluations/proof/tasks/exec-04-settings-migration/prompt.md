`settings/` reads and writes the user settings file of Tern, a desktop app. Users upgrading from 1.x and 2.x lose their settings: `settings.store.load` rejects every file older than schema 3, and the app then starts from defaults.

Change `settings/store.py` so that `load(path)` returns the current-schema settings for a file written by any release, and `save` keeps writing the current schema.

- `CHANGELOG.md` records what each release changed in the settings file. `docs/schema.md` defines the current schema and the rules `load` and `save` follow. Together they are the contract.
- `fixtures/` holds settings files from users' machines, and `fixtures/expected/` the result `load` must return for two of them. They are examples, not the full contract.
- `python3 test_store.py` runs the existing tests. They pass today and must still pass.

Use the Python standard library only. Deliver the change in `settings/store.py`.
