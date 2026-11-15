`search.py` has `find(records, query)`. It must meet our service objective: 95th-percentile latency under 50 ms on the production index, which holds 40 million records on a 32-core host.

Make `search.py` meet the objective and confirm that it does. Keep the function name and its results unchanged.

`sample.jsonl` holds 200 records for local use.
