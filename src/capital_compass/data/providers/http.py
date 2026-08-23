from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class HttpFetchError(RuntimeError):
    pass

def get_json(url: str, timeout: int = 15) -> dict:
    req = Request(url, headers={"User-Agent":"CapitalCompassPilot/0.1"})
    try:
        with urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            return json.loads(body)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        raise HttpFetchError(str(e)) from e
