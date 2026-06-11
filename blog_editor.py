#!/usr/bin/env python3
"""
Hugo Blog Editor
Run: python blog_editor.py
Opens a local web UI to write, preview, and push posts to GitHub.
"""

import http.server
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BLOG_DIR = Path(__file__).parent
POSTS_DIR = BLOG_DIR / "content" / "posts"

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hugo Blog Editor</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="window._katexReady = true; renderPreview()"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2e3147;
    --accent: #7c6af7; --accent2: #5eead4;
    --text: #e2e8f0; --muted: #8892a4; --danger: #f87171; --success: #34d399;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; height: 100vh; display: flex; flex-direction: column; }
  header { padding: 14px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; background: var(--surface); }
  header h1 { font-size: 1.1rem; font-weight: 600; color: var(--accent); flex: 1; }
  .tag { font-size: 0.7rem; background: #2e3147; color: var(--muted); padding: 2px 8px; border-radius: 99px; }
  .main { display: flex; flex: 1; overflow: hidden; }
  .panel { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
  .panel + .panel { border-left: 1px solid var(--border); }
  .panel-header { padding: 10px 16px; font-size: 0.75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
  .meta { padding: 16px; display: flex; flex-direction: column; gap: 10px; border-bottom: 1px solid var(--border); background: var(--surface); }
  .meta-row { display: flex; gap: 10px; }
  label { font-size: 0.75rem; color: var(--muted); display: block; margin-bottom: 4px; }
  input[type=text], input[type=date] {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    border-radius: 6px; padding: 7px 10px; font-size: 0.875rem; width: 100%;
    transition: border-color 0.15s;
  }
  input:focus { outline: none; border-color: var(--accent); }
  .flex1 { flex: 1; }
  .toggle-row { display: flex; align-items: center; gap: 8px; }
  .toggle { position: relative; width: 36px; height: 20px; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; inset: 0; background: var(--border); border-radius: 20px; cursor: pointer; transition: 0.2s; }
  .slider::before { content: ''; position: absolute; height: 14px; width: 14px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.2s; }
  input:checked + .slider { background: var(--accent); }
  input:checked + .slider::before { transform: translateX(16px); }
  .toggle-label { font-size: 0.8rem; color: var(--muted); }
  textarea {
    flex: 1; background: var(--bg); border: none; color: var(--text);
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.875rem; line-height: 1.7; padding: 16px; resize: none;
    tab-size: 2;
  }
  textarea:focus { outline: none; }
  .preview-body { flex: 1; overflow-y: auto; padding: 24px 32px; line-height: 1.8; font-size: 0.95rem; }
  /* Markdown-ish preview styles */
  .preview-body h1 { font-size: 1.8rem; margin: 1.5rem 0 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
  .preview-body h2 { font-size: 1.4rem; margin: 1.2rem 0 0.4rem; }
  .preview-body h3 { font-size: 1.1rem; margin: 1rem 0 0.3rem; color: var(--accent2); }
  .preview-body p { margin: 0.7rem 0; }
  .preview-body code { background: #1e2235; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.85em; color: var(--accent2); }
  .preview-body pre { background: #1e2235; padding: 14px; border-radius: 8px; overflow-x: auto; margin: 0.8rem 0; }
  .preview-body pre code { background: none; padding: 0; }
  .preview-body blockquote { border-left: 3px solid var(--accent); padding-left: 12px; color: var(--muted); margin: 0.8rem 0; }
  .preview-body ul, .preview-body ol { padding-left: 1.5rem; margin: 0.6rem 0; }
  .preview-body li { margin: 0.2rem 0; }
  .preview-body a { color: var(--accent); text-decoration: none; }
  .preview-body hr { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
  .preview-body .katex-display { margin: 1rem 0; overflow-x: auto; }
  footer { padding: 12px 20px; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 10px; background: var(--surface); }
  #status { flex: 1; font-size: 0.82rem; color: var(--muted); }
  #status.ok { color: var(--success); }
  #status.err { color: var(--danger); }
  button {
    padding: 8px 18px; border-radius: 6px; border: none; font-size: 0.85rem;
    font-weight: 600; cursor: pointer; transition: opacity 0.15s;
  }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-save { background: var(--border); color: var(--text); }
  .btn-push { background: var(--accent); color: white; }
  .btn-sync { background: #2a9d8f; color: white; }
  button:hover:not(:disabled) { opacity: 0.85; }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent2); }
</style>
</head>
<body>
<header>
  <div class="dot"></div>
  <h1>Hugo Blog Editor</h1>
  <span class="tag">lighton07.github.io</span>
</header>

<div class="main">
  <!-- LEFT: Editor -->
  <div class="panel">
    <div class="panel-header">✏️ Editor</div>
    <div class="meta">
      <div>
        <label>Title</label>
        <input type="text" id="title" placeholder="Post title..." oninput="renderPreview()">
      </div>
      <div class="meta-row">
        <div class="flex1">
          <label>Date</label>
          <input type="date" id="date">
        </div>
        <div class="flex1">
          <label>Tags (comma-separated)</label>
          <input type="text" id="tags" placeholder="math, tutorial" oninput="renderPreview()">
        </div>
        <div style="padding-top:20px">
          <div class="toggle-row">
            <label class="toggle">
              <input type="checkbox" id="math" checked onchange="renderPreview()">
              <span class="slider"></span>
            </label>
            <span class="toggle-label">KaTeX math</span>
          </div>
        </div>
      </div>
    </div>
    <textarea id="editor" placeholder="Write your post in Markdown...&#10;&#10;Inline math: $e^{i\pi} + 1 = 0$&#10;Block math: $$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$" oninput="renderPreview()"></textarea>
  </div>

  <!-- RIGHT: Preview -->
  <div class="panel">
    <div class="panel-header">👁 Preview</div>
    <div class="preview-body" id="preview"></div>
  </div>
</div>

<footer>
  <span id="status">Ready</span>
  <button class="btn-save" onclick="savePost()">💾 Save File</button>
  <button class="btn-push" onclick="pushPost()">🚀 Save &amp; Push to GitHub</button>
  <button class="btn-sync" onclick="syncAll()">🔄 Sync All Changes</button>
</footer>

<script>
// Set today's date
document.getElementById('date').value = new Date().toISOString().slice(0, 10);

// Simple Markdown renderer (no external dep needed for preview)
function mdToHtml(md) {
  let html = md
    // Protect math blocks from markdown processing
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, m) => `<span class="math-block">$$${m}$$</span>`)
    .replace(/\$([^\n$]+?)\$/g, (_, m) => `<span class="math-inline">$${m}$</span>`)
    // Headings
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold/italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Code blocks
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Blockquote
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // HR
    .replace(/^---$/gm, '<hr>')
    // Lists
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    // Links
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>')
    // Paragraphs
    .replace(/\n\n+/g, '\n\n')
    .split('\n\n')
    .map(block => {
      if (/^<(h[1-6]|pre|blockquote|hr|li|ul|ol)/.test(block.trim())) return block;
      if (block.trim() === '') return '';
      return `<p>${block.trim()}</p>`;
    })
    .join('\n');
  return html;
}

function renderPreview() {
  const title = document.getElementById('title').value;
  const body = document.getElementById('editor').value;
  const mathOn = document.getElementById('math').checked;

  let html = '';
  if (title) html += `<h1>${title}</h1>`;
  html += mdToHtml(body);

  // Restore math spans as actual math
  html = html
    .replace(/<span class="math-block">\$\$([\s\S]*?)\$\$<\/span>/g, '$$$$$$1$$$$')
    .replace(/<span class="math-inline">\$([^$]*?)\$<\/span>/g, '$$$1$');

  document.getElementById('preview').innerHTML = html;

  if (mathOn && window._katexReady) {
    renderMathInElement(document.getElementById('preview'), {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false }
      ],
      throwOnError: false
    });
  }
}

function buildFrontmatter() {
  const title = document.getElementById('title').value || 'Untitled';
  const date = document.getElementById('date').value;
  const tagsRaw = document.getElementById('tags').value;
  const math = document.getElementById('math').checked;
  const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);

  let fm = `---\ntitle: "${title}"\ndate: ${date}\n`;
  if (tags.length) fm += `tags: [${tags.map(t => `"${t}"`).join(', ')}]\n`;
  if (math) fm += `math: true\n`;
  fm += `---\n\n`;
  return fm;
}

function slugify(title) {
  return title.toLowerCase()
    .replace(/[^a-z0-9가-힣\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

async function post(endpoint, data) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

function setStatus(msg, type = '') {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = type;
}

async function savePost() {
  const title = document.getElementById('title').value || 'Untitled';
  const body = document.getElementById('editor').value;
  const content = buildFrontmatter() + body;
  const filename = slugify(title) || 'post';

  setStatus('Saving...');
  const result = await post('/api/save', { filename, content });
  if (result.ok) {
    setStatus(`✓ Saved: content/posts/${result.filename}`, 'ok');
  } else {
    setStatus(`✗ ${result.error}`, 'err');
  }
}

async function syncAll() {
  const msg = prompt('커밋 메시지:', 'chore: update blog files');
  if (!msg) return;
  setStatus('Committing and pushing all changes...');
  document.querySelectorAll('button').forEach(b => b.disabled = true);
  const result = await post('/api/sync', { message: msg });
  document.querySelectorAll('button').forEach(b => b.disabled = false);
  if (result.ok) {
    setStatus('✓ All changes pushed to GitHub!', 'ok');
  } else {
    setStatus(`✗ ${result.error}`, 'err');
  }
}

async function pushPost() {
  const title = document.getElementById('title').value || 'Untitled';
  const body = document.getElementById('editor').value;
  const content = buildFrontmatter() + body;
  const filename = slugify(title) || 'post';

  setStatus('Saving and pushing to GitHub...');
  document.querySelectorAll('button').forEach(b => b.disabled = true);

  const result = await post('/api/push', { filename, content, title });

  document.querySelectorAll('button').forEach(b => b.disabled = false);
  if (result.ok) {
    setStatus(`✓ Pushed! Live at: https://lighton07.github.io/posts/${filename}/`, 'ok');
  } else {
    setStatus(`✗ ${result.error}`, 'err');
  }
}
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress server logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        path = urlparse(self.path).path

        if path == "/api/save":
            result = self._save(body)
        elif path == "/api/push":
            result = self._push(body)
        elif path == "/api/sync":
            result = self._sync(body)
        else:
            result = {"ok": False, "error": "Unknown endpoint"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def _save(self, body):
        try:
            filename = body["filename"] + ".md"
            filepath = POSTS_DIR / filename
            POSTS_DIR.mkdir(parents=True, exist_ok=True)
            filepath.write_text(body["content"], encoding="utf-8")
            return {"ok": True, "filename": filename}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _push(self, body):
        try:
            # Save file first
            save_result = self._save(body)
            if not save_result["ok"]:
                return save_result

            title = body.get("title", "New post")
            filename = body["filename"] + ".md"

            # Git add, commit, push
            def run(cmd):
                r = subprocess.run(cmd, cwd=BLOG_DIR, capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr.strip() or r.stdout.strip())
                return r.stdout.strip()

            run(["git", "add", f"content/posts/{filename}"])
            run(["git", "commit", "-m", f"post: {title}"])
            run(["git", "push"])

            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _sync(self, body):
        try:
            message = body.get("message", "chore: update blog files")

            def run(cmd):
                r = subprocess.run(cmd, cwd=BLOG_DIR, capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr.strip() or r.stdout.strip())
                return r.stdout.strip()

            run(["git", "add", "-A"])
            # Check if there's anything to commit
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=BLOG_DIR, capture_output=True, text=True
            )
            if not status.stdout.strip():
                return {"ok": True, "note": "nothing to commit"}
            run(["git", "commit", "-m", message])
            run(["git", "push"])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def main():
    port = 8787
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"Hugo Blog Editor running at {url}")
    print("Press Ctrl+C to stop.\n")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
