"""Small read-only HTTP transport. No credentials, signing or transactions."""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

class SourceError(RuntimeError):
    pass

class JsonTransport:
    def __init__(self, timeout_seconds: float = 8.0, max_bytes: int = 2_000_000):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def request(self, url: str, *, payload: dict | None = None) -> dict | list:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json", "User-Agent": "MemeCoin-AI-Radar/0.1 (read-only research)"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                # Avoid loading unbounded responses from providers.
                chunk = response.read(self.max_bytes + 1)
                if len(chunk) > self.max_bytes:
                    raise SourceError("Provider response exceeded safety limit")
                return json.loads(chunk)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise SourceError(f"Provider unavailable or returned invalid JSON ({type(exc).__name__})") from exc
