`legacy_export` is a compiled tool our billing system has used for years. We are replacing it with Python.

Write `export.py` with a function `render(rows: list[dict]) -> str` whose output is byte-identical to `legacy_export` for every input, and confirm that it is.

`samples/` holds two input files and the output `legacy_export` produced for each.
