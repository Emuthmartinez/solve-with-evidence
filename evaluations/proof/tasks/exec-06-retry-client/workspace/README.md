# client

A thin wrapper around an HTTP transport. Our services use it to call upstream APIs.

| Path | What it is |
|---|---|
| `client/http.py` | `Client`, `Request`, `Response` and `TransportError`. |
| `docs/adr/` | Architecture decision records. A record is in force only while its status is Accepted. |
| `test_client.py` | The tests. Run them with `python3 test_client.py`. |

## Usage

```python
import time

from client.http import Client, Request

client = Client(transport, sleep=time.sleep, clock=time.monotonic)
response = client.send(Request('GET', 'https://api.example/orders/7', {}, None))
```

## Retries

`send()` retries any failed request up to 5 times, waiting one second between attempts.
