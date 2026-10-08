"""Smoke-check the running scaffold, static assets and PDF range support."""

import argparse
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def fetch(base, path, body=None, headers=None):
    headers = headers or {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    try:
        response = urlopen(Request(base + path, data=data, headers=headers), timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers, response.read()


def main(base):
    status, _, body = fetch(base, "/")
    assert status == 200, "Built frontend is not served"
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', body.decode())
    assert assets, "Frontend entry does not reference built assets"
    for asset in assets:
        assert fetch(base, asset)[0] == 200, "Frontend asset is unavailable"
    assert fetch(base, "/health/live")[0] == 200
    ready_status, _, ready_body = fetch(base, "/health/ready")
    assert ready_status in (200, 503)
    assert json.loads(ready_body)["model_probed"] is False
    status, _, body = fetch(base, "/api/demo", {"message": "connection test"})
    assert status == 200 and json.loads(body)["mode"] == "connection_test"
    status, headers, body = fetch(base, "/api/documents/flexi-ulife-prime-saver", headers={"Range": "bytes=0-4"})
    assert status == 206 and body == b"%PDF-", "PDF range response failed"
    assert "inline" in headers["Content-Disposition"]
    assert fetch(base, "/.env")[0] == 404
    assert fetch(base, "/api/documents/unknown")[0] == 404
    print("Homepage, built assets, health, demo, PDF ranges and file isolation: OK")
    print(f"RAG dependency readiness: HTTP {ready_status}; no model API was called.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    main(parser.parse_args().base.rstrip("/"))
