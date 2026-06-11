import http.server, json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from . import posts, folders, homepage, git

STATIC = Path(__file__).parent / 'static'

MIME = {'.html': 'text/html', '.css': 'text/css',
        '.js': 'application/javascript', '.ico': 'image/x-icon'}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == '/api/tree':
            return self._json(folders.build_tree())
        if path == '/api/folders':
            return self._json(folders.list_flat())
        if path == '/api/homepage':
            return self._json(homepage.read())
        if path == '/api/post':
            fp = qs.get('file', [None])[0]
            data = posts.read(fp) if fp else None
            return self._json(data or {"ok": False, "error": "not found"})

        # Static files
        if path in ('/', '/index.html'):
            return self._static(STATIC / 'index.html', 'text/html')
        fp = STATIC / path.lstrip('/')
        if fp.exists() and fp.is_file():
            return self._static(fp, MIME.get(fp.suffix, 'text/plain'))

        self.send_error(404)

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        path = urlparse(self.path).path
        handlers = {
            '/api/save':          self._save,
            '/api/push':          self._push,
            '/api/sync':          self._sync,
            '/api/save-homepage': self._save_homepage,
            '/api/create-folder': self._create_folder,
            '/api/move':          self._move,
        }
        fn = handlers.get(path)
        self._json(fn(body) if fn else {"ok": False, "error": "unknown endpoint"})

    # ── helpers ───────────────────────────────────────────────────────────────
    def _json(self, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, fp, mime):
        data = Path(fp).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    # ── API handlers ──────────────────────────────────────────────────────────
    def _save(self, b):
        try:
            path = posts.save(b['path'], b['content'], b.get('oldPath'))
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _push(self, b):
        try:
            posts.save(b['path'], b['content'], b.get('oldPath'))
            return git.commit_and_push(f"post: {b.get('title','update')}")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _sync(self, b):
        try:
            return git.commit_and_push(b.get('message', 'chore: update'))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _save_homepage(self, b):
        try:
            homepage.write(b.get('name',''), b.get('bio',''), b.get('education',[]))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _create_folder(self, b):
        try:
            path = folders.create(b.get('path', b.get('name', '')))
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _move(self, b):
        try:
            t = b.get('type')
            frm = b.get('from', '')
            to = b.get('toParent', '')
            if t == 'post':
                new = folders.move_post(frm, to)
            elif t == 'folder':
                new = folders.move_folder(frm, to)
            else:
                return {"ok": False, "error": "unknown type"}
            return {"ok": True, "newPath": new}
        except Exception as e:
            return {"ok": False, "error": str(e)}
