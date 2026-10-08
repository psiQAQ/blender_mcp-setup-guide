"""Serve the current static site on loopback without browser caching."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from build_cache import LATEST


class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=LATEST / 'site')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    if not (args.site / 'index.html').is_file():
        raise FileNotFoundError(args.site / 'index.html')
    with ThreadingHTTPServer(('127.0.0.1', args.port), partial(PreviewHandler, directory=str(args.site.resolve()))) as server:
        print(f'http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
