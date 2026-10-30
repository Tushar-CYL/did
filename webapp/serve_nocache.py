"""Serve the static export (out/) with no-cache headers so the browser never shows a stale build."""
import http.server
import os
import socketserver
import sys
from pathlib import Path

# 3100 by default so this can run at the SAME TIME as "npm run dev" (port 3000).
#   python webapp/serve_nocache.py          -> 3100
#   python webapp/serve_nocache.py 8080     -> 8080
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("ACCOUNTSIGNAL_UI_PORT", 3100))
ROOT = Path(__file__).resolve().parent / "out"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    protocol_version = "HTTP/1.1"  # keep-alive, so the browser reuses connections cleanly

    def log_message(self, *args):
        pass


# Threaded + daemon threads so a browser's many parallel requests (HTML + CSS + JS + data.json) are all
# served at once; the old single-threaded server stalled when Chrome opened several connections.
class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


with Server(("127.0.0.1", PORT), Handler) as httpd:
    print(f"Serving {ROOT} at http://localhost:{PORT} (no-cache, threaded)")
    httpd.serve_forever()
