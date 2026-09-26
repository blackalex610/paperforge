"""Serve the api/ functions locally on :8787, the way Vercel routes them.

    python scripts/dev_server.py      # then, in another shell: npm run dev
"""
from __future__ import annotations

import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.catalog import handler as catalog  # noqa: E402
from api.generate import handler as generate  # noqa: E402

ROUTES = {"/api/generate": generate, "/api/catalog": catalog}


class Router(generate):
    def do_GET(self) -> None:
        route = ROUTES.get(urlparse(self.path).path)
        if route is None:
            self._send(404, {"error": "not found"}, "no-store")
        else:
            route.do_GET(self)


if __name__ == "__main__":
    print("paperforge api on http://127.0.0.1:8787")
    ThreadingHTTPServer(("127.0.0.1", 8787), Router).serve_forever()
