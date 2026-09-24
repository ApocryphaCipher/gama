"""Client for the DOSBox Staging fork's HTTP API (localhost only)."""

import json
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8086"
MEMORY_SIZE = 16 * 1024 * 1024


class DosboxApi:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 30):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, method: str = "GET") -> bytes:
        req = urllib.request.Request(f"{self.url}{path}", method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as res:
            return res.read()

    def info(self) -> dict:
        return json.loads(self._request("/api/v1/dosbox/info"))

    def memory(self) -> bytes:
        return self._request(f"/api/v1/memory/0/{MEMORY_SIZE}")

    def cpu_state(self) -> bytes:
        return self._request("/api/v1/cpu/state")

    def screenshot(self, kind: str = "raw") -> bytes:
        return self._request(f"/api/v1/capture/screenshot?type={kind}&inline=1", method="POST")
