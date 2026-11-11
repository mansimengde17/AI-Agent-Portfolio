# Client Library Usage

## Creating a client

Use `create_client` to construct a client handle. The `timeout` parameter
defaults to 30 seconds and `retries` defaults to 3:

```python
client = create_client(api_key="sk-live-...", timeout=30, retries=3)
```

## Fetching records

Call `fetch_records` with your `dataset` name. Pagination is controlled by
the `page_size` parameter, which defaults to 100.

```python
rows = fetch_records(client, dataset="events", page_size=100)
```

## Configuration

The module-level constant `DEFAULT_TIMEOUT` mirrors the client default and
is safe to import directly.
