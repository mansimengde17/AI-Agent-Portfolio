"""Miniature target project: a small API client used by the demo."""

DEFAULT_TIMEOUT = 30


def create_client(api_key, base_url="https://api.example.com",
                  timeout=30, retries=3):
    """Create a configured API client.

    Returns a dict-based client handle used by fetch_records.
    """
    return {"api_key": api_key, "base_url": base_url,
            "timeout": timeout, "retries": retries}


def fetch_records(client, dataset, page_size=100):
    """Fetch records from a dataset, paginated by page_size."""
    return {"client": client, "dataset": dataset, "page_size": page_size,
            "records": []}
