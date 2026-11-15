`importer/` is the nightly job that imports our bank's transaction export into the ledger. Last night it rejected `data/export-sample.csv`, a real export. `docs/FORMAT.md` is the bank's description of the format, and it is the authority.

Make `importer.load(path)` import every file that follows `docs/FORMAT.md` and raise `FormatError` for every file that breaks it.

- The sample is one real file. Other nights' files use parts of the format that this one does not.
- Everything else in the package must keep working as documented.
- `python3 test_reader.py` runs the existing tests. They pass today and must still pass. They are examples, not the full contract.

Use the Python standard library only. Deliver the change in `importer/reader.py`. Other files in the package may change too.
