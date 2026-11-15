# importer

The nightly job that imports the bank's transaction export into the ledger.

| File | What it does |
|---|---|
| `importer/reader.py` | `load(path)` reads one export file into a list of `Transaction`s. |
| `importer/model.py` | `Transaction`, the record the ledger receives, and `FormatError`. |
| `importer/money.py` | `parse_amount` turns an amount into integer minor units. It is shared by the reader and by `importer/statement.py`. |
| `importer/statement.py` | `parse_adjustment` parses the manual adjustments that back-office staff type into the ledger. Staff write English notation, such as `1,234.56 EUR`. |
| `docs/FORMAT.md` | The bank's description of the export format. |
| `data/currencies.csv` | Each currency code and the number of decimals of its minor unit. `load` reads it from here. |
| `data/export-sample.csv` | Last night's export. |

Run the tests with `python3 test_reader.py`.
