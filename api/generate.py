"""GET /api/generate — one verified exam paper as JSON.

Query parameters (all optional):
  blueprint   nvo2026 | classic            (default nvo2026)
  difficulty  easy | medium | actual | extra_hard   (default actual)
  seed        0 … 4294967295               (default: random)
  short       1 for the short practice form
  key         0 to leave the answer key out

A seeded request is a pure function of its query string, so it is cached at
the edge for a year. An unseeded one picks a seed, reports it in
``meta.seed``, and is never cached.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperforge.service import BadRequest, generate  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = {k: v[-1] for k, v in parse_qs(urlparse(self.path).query).items()}
        try:
            body = generate(
                blueprint=query.get("blueprint"),
                difficulty=query.get("difficulty"),
                seed=query.get("seed"),
                short=query.get("short") in ("1", "true"),
                include_key=query.get("key") not in ("0", "false"),
            )
            status = 200
            cache = ("public, max-age=3600, s-maxage=31536000, immutable"
                     if query.get("seed") else "no-store")
        except BadRequest as exc:
            body, status, cache = {"error": str(exc)}, 400, "no-store"
        except Exception as exc:  # a paper that fails verification is never served
            body, status, cache = {"error": f"generation failed: {exc}"}, 500, "no-store"
        self._send(status, body, cache)

    def _send(self, status: int, body: dict, cache: str) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", cache)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
