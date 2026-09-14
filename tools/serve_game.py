"""Serve the Godot web export and proxy its same-origin API requests locally."""

from __future__ import annotations

import argparse
import http.client
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class GameHandler(SimpleHTTPRequestHandler):
    backend = "http://127.0.0.1:8000"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy()
        else:
            self.send_error(404)

    def proxy(self):
        target = urlsplit(self.backend)
        factory = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        connection = factory(target.hostname, target.port, timeout=60)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 65536:
                self.send_error(413)
                return
            body = self.rfile.read(length) if length else None
            connection.request(self.command, self.path, body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            content = response.read()
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (OSError, http.client.HTTPException, ValueError):
            self.send_error(502, "Poker API unavailable. Start the backend on port 8000.")
        finally:
            connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5174)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "game" / "build" / "web"
    if not (root / "index.html").exists():
        parser.error('Export first: godot --headless --path game --export-release Web')
    GameHandler.backend = args.backend
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(GameHandler, directory=str(root)))
    print(f"Godot poker: http://localhost:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
