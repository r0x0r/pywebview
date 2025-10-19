"""
This script starts a simple no-caching HTTP server that serves files from the current directory.
"""

import os
from http import server


class NoCacheHTTPRequestHandler(server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


os.chdir(os.path.dirname(os.path.abspath(__file__)))
server.HTTPServer(('', 1234), NoCacheHTTPRequestHandler).serve_forever()
