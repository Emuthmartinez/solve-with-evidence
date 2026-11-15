`client/http.py` wraps an HTTP transport for our services. `Client.send` makes one attempt and never retries.

Implement retries in `Client.send` as the accepted decision records in `docs/adr` decide.

- Where accepted records disagree, the later one wins.
- `README.md` is out of date about retries.
- `python3 test_client.py` runs the existing tests. They pass today and must still pass. They are examples, not the full contract.

Also deliver `test_retries.py` in this directory: tests that prove the retry rules hold. It is run as `python3 test_retries.py` from this directory, and exit status 0 means every test passed.

- It must pass on your client and on any other client that follows the accepted records. So it may use only the public interface those records define, with a fake transport, a fake `sleep` and a fake `clock`.
- It must fail on a client that breaks any one retry rule of the accepted records.
- No real waiting and no network.

Use the Python standard library only. Deliver `client/http.py` and `test_retries.py`.
