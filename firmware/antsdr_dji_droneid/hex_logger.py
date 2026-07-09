#!/usr/bin/env python3
"""
Minimal O4 hex capture server for AntSDR E200 (no license required).

The E200 O4 firmware POSTs encrypted DroneID to:
  GET /api/o4online/decrypt?hex=<payload>

Run this on your PC (same machine as api_host in fw_setenv), then point:
  fw_setenv api_host <your-pc-ip>

Logs every hex payload to o4_encrypted_hex.log and prints a short preview.
"""
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs


LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "o4_encrypted_hex.log")
LISTEN_ADDR = os.environ.get("HEX_LOGGER_ADDR", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("HEX_LOGGER_PORT", "80"))


class HexHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/o4online/decrypt":
            params = parse_qs(parsed.query)
            hex_payload = params.get("hex", [None])[0]
            if hex_payload:
                line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {hex_payload}\n"
                with open(LOG_FILE, "a") as f:
                    f.write(line)
                preview = hex_payload[:64] + ("..." if len(hex_payload) > 64 else "")
                print(f"HEX ({len(hex_payload)} chars): {preview}")
            self._json(b'{"sn": ""}')
        elif parsed.path == "/health":
            self._json(b'{"status":"ok","service":"hex_logger"}')
        else:
            self._json(b'{"error":"not found"}', 404)

    def _json(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    print("O4 Hex Logger (no license needed)")
    print(f"  Listen: {LISTEN_ADDR}:{LISTEN_PORT}")
    print(f"  Log:    {LOG_FILE}")
    print("  Set on E200: fw_setenv api_host <this-pc-ip>")
    print()
    server = ThreadedServer((LISTEN_ADDR, LISTEN_PORT), HexHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
