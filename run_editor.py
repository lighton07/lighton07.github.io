#!/usr/bin/env python3
"""Hugo Blog Editor — entry point.  Run: python run_editor.py"""
import http.server, threading, webbrowser
from editor.server import Handler

PORT = 8787

def main():
    server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    url = f'http://localhost:{PORT}'
    print(f'Blog Editor -> {url}  (Ctrl+C to stop)')
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')

if __name__ == '__main__':
    main()
