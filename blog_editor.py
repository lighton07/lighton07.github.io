#!/usr/bin/env python3
"""Hugo Blog Editor v3 — folder/section support"""

import http.server, json, re, subprocess, threading, webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BLOG_DIR  = Path(__file__).parent
POSTS_DIR = BLOG_DIR / "content" / "posts"
HUGO_TOML = BLOG_DIR / "hugo.toml"
HOME_INFO = BLOG_DIR / "layouts" / "partials" / "home_info.html"

# ── helpers ──────────────────────────────────────────────────────────────────

def run_git(*cmd):
    r = subprocess.run(["git"] + list(cmd), cwd=BLOG_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()

def parse_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---\n?(.*)', text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip().strip('"')
    return fm, m.group(2).lstrip('\n')

def norm(p):
    """Normalize Path to forward-slash string."""
    return str(p).replace('\\', '/')

def list_posts():
    posts = []
    for f in sorted(POSTS_DIR.rglob("*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name == '_index.md':
            continue
        rel = f.relative_to(POSTS_DIR)
        folder = norm(rel.parent) if rel.parent != Path('.') else ''
        try:
            fm, _ = parse_frontmatter(f.read_text(encoding='utf-8'))
            posts.append({"file": norm(rel), "folder": folder,
                          "title": fm.get("title", f.stem),
                          "date": fm.get("date", ""), "tags": fm.get("tags", "")})
        except Exception:
            posts.append({"file": norm(rel), "folder": folder,
                          "title": f.stem, "date": "", "tags": ""})
    return posts

def list_folders():
    folders = []
    if POSTS_DIR.exists():
        for d in sorted(POSTS_DIR.iterdir()):
            if d.is_dir():
                count = len([f for f in d.glob("*.md") if f.name != "_index.md"])
                folders.append({"name": d.name, "count": count})
    return folders

def read_homepage():
    toml = HUGO_TOML.read_text(encoding="utf-8") if HUGO_TOML.exists() else ""
    name = re.search(r'Title\s*=\s*"([^"]*)"', toml)
    bio  = re.search(r'Content\s*=\s*"([^"]*)"', toml)
    name = name.group(1) if name else "Lighton"
    bio  = bio.group(1)  if bio  else ""
    entries = []
    if HOME_INFO.exists():
        html = HOME_INFO.read_text(encoding="utf-8")
        for block in re.finditer(
            r'<div class="cv-entry">(.*?)<span class="cv-period">(.*?)</span>\s*</div>',
            html, re.DOTALL):
            inner = block.group(1)
            s = re.search(r'class="cv-school">(.*?)<', inner)
            d = re.search(r'class="cv-degree">(.*?)<', inner)
            entries.append({"school": s.group(1) if s else "",
                            "degree": d.group(1) if d else "",
                            "period": block.group(2).strip()})
    return {"name": name, "bio": bio, "education": entries}

def write_homepage(name, bio, education):
    toml = HUGO_TOML.read_text(encoding="utf-8")
    toml = re.sub(r'(\[params\.homeInfoParams\]\s*\n\s*Title\s*=\s*)"[^"]*"',
                  f'\\1"{name}"', toml)
    toml = re.sub(r'(Content\s*=\s*)"[^"]*"', f'\\1"{bio}"', toml)
    HUGO_TOML.write_text(toml, encoding="utf-8")

    edu_html = ""
    for e in education:
        edu_html += f"""
        <div class="cv-entry">
          <div class="cv-entry-left">
            <span class="cv-school">{e['school']}</span>
            <span class="cv-degree">{e['degree']}</span>
          </div>
          <span class="cv-period">{e['period']}</span>
        </div>"""

    html = (
        '{{- with site.Params.homeInfoParams }}\n'
        '<article class="first-entry home-info">\n'
        '    <header class="entry-header">\n'
        '        <h1>{{{{ .Title | markdownify }}}}</h1>\n'
        '    </header>\n'
        '    <div class="entry-content md-content">\n'
        '        {{{{ $opts := dict "display" "block" }}}}\n'
        '        {{{{ .Content | $.Page.RenderString $opts }}}}\n'
        '    </div>\n\n'
        '    <div class="cv-section">\n'
        '      <h2 class="cv-title">학력</h2>\n'
        f'      <div class="cv-entries">{edu_html}\n      </div>\n'
        '    </div>\n\n'
        '    <footer class="entry-footer">\n'
        '        {{{{ partial "social_icons.html" (dict "align" site.Params.homeInfoParams.AlignSocialIconsTo) }}}}\n'
        '    </footer>\n'
        '</article>\n'
        '{{- end -}}\n\n'
        '<style>\n'
        '.cv-section{margin-top:1.2rem;padding-top:1rem;border-top:1px solid var(--border)}\n'
        '.cv-title{font-size:.72rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:.1em;color:var(--secondary);margin:0 0 .75rem}\n'
        '.cv-entries{display:flex;flex-direction:column;gap:.6rem}\n'
        '.cv-entry{display:flex;align-items:baseline;justify-content:space-between;gap:1rem}\n'
        '.cv-entry-left{display:flex;gap:.5rem;align-items:baseline}\n'
        '.cv-school{font-weight:600;font-size:.9rem}\n'
        '.cv-degree{font-size:.82rem;color:var(--secondary)}\n'
        '.cv-period{font-size:.8rem;color:var(--secondary);white-space:nowrap;flex-shrink:0}\n'
        '</style>\n'
    )
    HOME_INFO.parent.mkdir(parents=True, exist_ok=True)
    HOME_INFO.write_text(html, encoding="utf-8")

# ── HTML ─────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blog Editor</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="window._katexReady=true;renderPreview()"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#111113;--surface:#18181c;--surface2:#222228;
  --border:#2a2a34;--accent:#7c6af7;--accent2:#5eead4;
  --text:#dde1ec;--muted:#6e738a;--danger:#f87171;--success:#34d399;
}
body{background:var(--bg);color:var(--text);
  font-family:'Segoe UI',system-ui,sans-serif;height:100vh;
  display:flex;flex-direction:column;overflow:hidden}

/* topbar */
.topbar{display:flex;align-items:center;gap:10px;padding:0 14px;height:44px;
  background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
.topbar-title{font-size:.88rem;font-weight:700;color:var(--accent);flex:1}
.topbar-url{font-size:.7rem;color:var(--muted);background:var(--surface2);
  padding:2px 9px;border-radius:99px}
#status{font-size:.77rem;color:var(--muted);max-width:340px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#status.ok{color:var(--success)}
#status.err{color:var(--danger)}
.btn{padding:5px 13px;border-radius:6px;border:none;font-size:.78rem;
  font-weight:600;cursor:pointer;transition:opacity .15s;white-space:nowrap}
.btn:disabled{opacity:.35;cursor:not-allowed}
.btn:hover:not(:disabled){opacity:.8}
.btn-ghost{background:var(--surface2);color:var(--text)}
.btn-primary{background:var(--accent);color:#fff}
.btn-green{background:#2a9d8f;color:#fff}

/* workspace */
.workspace{display:flex;flex:1;overflow:hidden}

/* sidebar */
.sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column;
  background:var(--surface);border-right:1px solid var(--border);overflow:hidden}
.sidebar-top{display:flex;gap:6px;padding:10px 10px 6px;flex-shrink:0}
.sidebar-top .btn{flex:1;font-size:.75rem;padding:5px 0}
.folder-tree{flex:1;overflow-y:auto;padding:4px 0}
.folder-group{margin:1px 0}
.folder-label{display:flex;align-items:center;gap:6px;padding:6px 10px;
  cursor:pointer;border-radius:6px;margin:0 5px;font-size:.81rem;
  color:var(--text);transition:background .1s;user-select:none}
.folder-label:hover{background:var(--surface2)}
.folder-label .arrow{font-size:.6rem;color:var(--muted);width:8px;flex-shrink:0;
  transition:transform .15s}
.folder-label.open .arrow{transform:rotate(90deg)}
.folder-icon{font-size:.85rem}
.folder-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.folder-badge{font-size:.65rem;color:var(--muted);background:var(--surface2);
  padding:1px 5px;border-radius:99px;flex-shrink:0}
.folder-children{overflow:hidden}
.post-item{padding:5px 10px 5px 28px;cursor:pointer;border-radius:5px;
  margin:0 5px;transition:background .1s}
.post-item:hover{background:var(--surface2)}
.post-item.active{background:#29293e}
.post-item-title{font-size:.79rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.post-item-date{font-size:.67rem;color:var(--muted);margin-top:1px}
.sidebar-divider{height:1px;background:var(--border);margin:5px 10px}
.sidebar-footer{padding:5px 5px 10px;flex-shrink:0}
.sidebar-nav-btn{display:flex;align-items:center;gap:7px;padding:7px 10px;
  font-size:.81rem;cursor:pointer;border-radius:6px;margin:1px 0;
  color:var(--text);transition:background .1s;user-select:none}
.sidebar-nav-btn:hover{background:var(--surface2)}
.sidebar-nav-btn.active{background:var(--accent);color:#fff}

/* panes */
.pane{display:flex;flex-direction:column;flex:1;overflow:hidden;min-width:0}
.pane+.pane{border-left:1px solid var(--border)}
.pane-header{padding:7px 13px;font-size:.69rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  background:var(--surface);border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:7px;flex-shrink:0}
.pane-badge{color:var(--accent);font-size:.68rem;text-transform:none;letter-spacing:0}

/* editor meta */
.editor-meta{padding:10px 13px;display:flex;flex-direction:column;gap:7px;
  background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
.meta-row{display:flex;gap:7px;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:3px}
.field label{font-size:.68rem;color:var(--muted)}
.field.grow{flex:1}
input[type=text],input[type=date],textarea,select{
  background:var(--bg);border:1px solid var(--border);color:var(--text);
  border-radius:5px;padding:5px 8px;font-size:.81rem;width:100%;
  font-family:inherit;transition:border-color .15s}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent)}
select option{background:var(--surface2)}
.toggle-wrap{display:flex;align-items:center;gap:5px;padding-bottom:2px}
.toggle{position:relative;width:30px;height:16px;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:var(--border);
  border-radius:16px;cursor:pointer;transition:.18s}
.slider::before{content:'';position:absolute;height:10px;width:10px;
  left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.18s}
input:checked+.slider{background:var(--accent)}
input:checked+.slider::before{transform:translateX(14px)}
.toggle-label{font-size:.72rem;color:var(--muted)}
textarea.main-editor{flex:1;border:none;border-radius:0;resize:none;
  font-family:'Cascadia Code','Fira Code',Consolas,monospace;
  font-size:.84rem;line-height:1.75;padding:13px;tab-size:2}

/* homepage editor */
.hp-editor{flex:1;overflow-y:auto;padding:14px}
.hp-section{margin-bottom:18px}
.hp-section h3{font-size:.69rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:var(--muted);margin-bottom:9px;
  padding-bottom:5px;border-bottom:1px solid var(--border)}
.edu-entry{display:flex;gap:7px;align-items:flex-end;margin-bottom:7px;
  background:var(--surface2);padding:7px;border-radius:7px}
.edu-entry .field{flex:1}
.edu-del{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:.95rem;padding:0 3px;align-self:center}
.edu-del:hover{color:var(--danger)}
.btn-add{background:none;border:1px dashed var(--border);color:var(--muted);
  border-radius:6px;padding:5px 10px;font-size:.76rem;cursor:pointer;width:100%;
  transition:border-color .15s,color .15s}
.btn-add:hover{border-color:var(--accent);color:var(--accent)}

/* PaperMod preview */
.preview-pane{flex:1;overflow-y:auto;
  background:#1d1e20;color:rgba(255,255,255,.84);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
.pm-nav{display:flex;align-items:center;justify-content:space-between;
  padding:11px 22px;border-bottom:1px solid #383840;
  background:#1d1e20;position:sticky;top:0;z-index:10}
.pm-nav-title{font-size:.95rem;font-weight:700;color:rgba(255,255,255,.84)}
.pm-nav-links{display:flex;gap:14px}
.pm-nav-link{font-size:.8rem;color:rgba(255,255,255,.5)}
.pm-wrap{max-width:740px;margin:0 auto;padding:18px 22px 60px}
.pm-post-title{font-size:1.85rem;font-weight:700;line-height:1.3;
  color:rgba(255,255,255,.84);margin-bottom:7px}
.pm-post-meta{font-size:.78rem;color:rgba(255,255,255,.5);
  display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.pm-post-body{line-height:1.85;color:rgba(255,255,255,.74);font-size:.96rem}
.pm-post-body h1{font-size:1.65rem;font-weight:700;margin:1.8rem 0 .5rem;
  color:rgba(255,255,255,.84);border-bottom:1px solid #383840;padding-bottom:.3rem}
.pm-post-body h2{font-size:1.3rem;font-weight:700;margin:1.5rem 0 .4rem;
  color:rgba(255,255,255,.84)}
.pm-post-body h3{font-size:1.05rem;font-weight:600;margin:.9rem 0 .3rem;
  color:rgba(255,255,255,.7)}
.pm-post-body p{margin:.65rem 0}
.pm-post-body a{color:#7c6af7;text-decoration:none}
.pm-post-body code{background:rgba(255,255,255,.07);padding:2px 5px;
  border-radius:4px;font-family:monospace;font-size:.84em;color:#5eead4}
.pm-post-body pre{background:rgba(255,255,255,.03);border:1px solid #383840;
  border-radius:7px;padding:13px;overflow-x:auto;margin:.85rem 0}
.pm-post-body pre code{background:none;padding:0;color:inherit}
.pm-post-body blockquote{border-left:3px solid #7c6af7;padding-left:11px;
  color:rgba(255,255,255,.55);margin:.85rem 0}
.pm-post-body ul,.pm-post-body ol{padding-left:1.5rem;margin:.55rem 0}
.pm-post-body li{margin:.22rem 0}
.pm-post-body hr{border:none;border-top:1px solid #383840;margin:1.4rem 0}
.pm-post-body .katex-display{margin:1.1rem 0;overflow-x:auto}
/* homepage preview */
.pm-home-info{border:1px solid #383840;border-radius:11px;padding:18px 22px;
  margin-bottom:22px;background:#2e2e33}
.pm-home-info h1{font-size:1.5rem;font-weight:700;margin-bottom:7px}
.pm-home-info p{font-size:.88rem;color:rgba(255,255,255,.68);
  line-height:1.7;margin-bottom:12px}
.pm-cv-divider{border:none;border-top:1px solid #383840;margin:10px 0 9px}
.pm-cv-label{font-size:.63rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:rgba(255,255,255,.38);margin-bottom:7px}
.pm-cv-row{display:flex;justify-content:space-between;align-items:baseline;
  margin-bottom:4px}
.pm-cv-school{font-weight:600;font-size:.86rem}
.pm-cv-deg{font-size:.76rem;color:rgba(255,255,255,.48);margin-left:5px}
.pm-cv-period{font-size:.74rem;color:rgba(255,255,255,.38);white-space:nowrap}
/* folder home preview */
.pm-folder-layout{display:grid;grid-template-columns:160px 1fr;gap:18px}
.pm-folder-nav{}
.pm-folder-nav-title{font-size:.63rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:rgba(255,255,255,.35);margin-bottom:8px}
.pm-folder-item{display:flex;justify-content:space-between;align-items:center;
  padding:6px 10px;border-radius:7px;margin-bottom:4px;
  border:1px solid #383840;font-size:.82rem;cursor:pointer;transition:border-color .15s}
.pm-folder-item:hover{border-color:#7c6af7}
.pm-folder-item-name{color:rgba(255,255,255,.75)}
.pm-folder-item-count{font-size:.7rem;color:rgba(255,255,255,.38)}
.pm-recent-title{font-size:.63rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:rgba(255,255,255,.35);margin-bottom:8px}
.pm-post-card{border:1px solid #383840;border-radius:9px;padding:11px 15px;
  margin-bottom:8px;background:#2e2e33;transition:border-color .15s;cursor:pointer}
.pm-post-card:hover{border-color:#7c6af7}
.pm-card-title{font-size:.93rem;font-weight:600;margin-bottom:3px}
.pm-card-meta{font-size:.72rem;color:rgba(255,255,255,.42)}
.pm-card-folder{font-size:.67rem;color:#7c6af7;margin-top:2px}
</style>
</head>
<body>

<div class="topbar">
  <span class="topbar-title">✦ Blog Editor</span>
  <span class="topbar-url">lighton07.github.io</span>
  <span id="status">준비됨</span>
  <button class="btn btn-ghost" onclick="saveCurrentFile()">💾 저장</button>
  <button class="btn btn-primary" onclick="pushCurrent()">🚀 Push</button>
  <button class="btn btn-green" onclick="syncAll()">🔄 Sync All</button>
</div>

<div class="workspace">

  <!-- sidebar -->
  <div class="sidebar">
    <div class="sidebar-top">
      <button class="btn btn-ghost" onclick="newPost()">✚ 새 글</button>
      <button class="btn btn-ghost" onclick="promptNewFolder()" title="새 폴더 만들기">📁+</button>
    </div>
    <div class="folder-tree" id="folder-tree"></div>
    <div class="sidebar-divider"></div>
    <div class="sidebar-footer">
      <div class="sidebar-nav-btn" id="btn-homepage" onclick="openHomepage()">🏠 Main Page</div>
    </div>
  </div>

  <!-- post editor -->
  <div class="pane" id="pane-post">
    <div class="pane-header">
      ✏️ 에디터
      <span class="pane-badge" id="editing-label"></span>
    </div>
    <div class="editor-meta">
      <div class="field">
        <label>제목</label>
        <input type="text" id="post-title" placeholder="글 제목..." oninput="renderPreview()">
      </div>
      <div class="meta-row">
        <div class="field">
          <label>날짜</label>
          <input type="date" id="post-date">
        </div>
        <div class="field">
          <label>폴더</label>
          <select id="post-folder" onchange="onFolderChange()">
            <option value="">(미분류)</option>
          </select>
        </div>
        <div class="field grow">
          <label>태그</label>
          <input type="text" id="post-tags" placeholder="math, cs" oninput="renderPreview()">
        </div>
        <div class="toggle-wrap" style="padding-bottom:5px">
          <label class="toggle">
            <input type="checkbox" id="post-math" checked onchange="renderPreview()">
            <span class="slider"></span>
          </label>
          <span class="toggle-label">KaTeX</span>
        </div>
      </div>
    </div>
    <textarea class="main-editor" id="post-body"
      placeholder="Markdown으로 작성하세요..."
      oninput="renderPreview()"></textarea>
  </div>

  <!-- homepage editor -->
  <div class="pane" id="pane-homepage" style="display:none">
    <div class="pane-header">🏠 메인 페이지 편집</div>
    <div class="hp-editor">
      <div class="hp-section">
        <h3>프로필</h3>
        <div class="field" style="margin-bottom:7px">
          <label>이름</label>
          <input type="text" id="hp-name" oninput="renderPreview()">
        </div>
        <div class="field">
          <label>소개글</label>
          <textarea id="hp-bio" rows="3" style="resize:vertical" oninput="renderPreview()"></textarea>
        </div>
      </div>
      <div class="hp-section">
        <h3>학력</h3>
        <div id="edu-list"></div>
        <button class="btn-add" onclick="addEduEntry()">+ 항목 추가</button>
      </div>
    </div>
  </div>

  <!-- preview -->
  <div class="pane preview-pane">
    <div class="pm-nav">
      <span class="pm-nav-title" id="preview-site-title">Lighton</span>
      <div class="pm-nav-links">
        <span class="pm-nav-link">Posts</span>
        <span class="pm-nav-link">Tags</span>
      </div>
    </div>
    <div class="pm-wrap" id="preview-content"></div>
  </div>

</div>

<script>
// ── state ────────────────────────────────────────────────────────────────────
let mode = 'post';
let currentFile = null;   // full relative path e.g. "math/foo.md" or "hello.md"
let allPosts = [];
let allFolders = [];
let expandedFolders = new Set();
let eduEntries = [];

// ── init ─────────────────────────────────────────────────────────────────────
document.getElementById('post-date').value = new Date().toISOString().slice(0,10);
loadAll();

async function loadAll() {
  const [postsRes, foldersRes] = await Promise.all([
    fetch('/api/posts').then(r => r.json()),
    fetch('/api/folders').then(r => r.json())
  ]);
  allPosts = postsRes;
  allFolders = foldersRes;
  // auto-expand folders that have the current file
  for (const f of allFolders) expandedFolders.add(f.name);
  renderFolderTree();
  updateFolderSelect();
}

// ── folder tree ───────────────────────────────────────────────────────────────
function renderFolderTree() {
  const ROOT = '';
  const groups = {};
  for (const p of allPosts) {
    const key = p.folder || ROOT;
    if (!groups[key]) groups[key] = [];
    groups[key].push(p);
  }

  // Sort: named folders first (alphabetical), root last
  const keys = Object.keys(groups).sort((a, b) => {
    if (a === ROOT) return 1;
    if (b === ROOT) return -1;
    return a.localeCompare(b, 'ko');
  });

  let html = '';
  for (const key of keys) {
    const posts = groups[key];
    const isRoot = key === ROOT;
    const label = isRoot ? '미분류' : key;
    const icon  = isRoot ? '📄' : '📁';
    const open  = expandedFolders.has(key) || isRoot;

    html += `<div class="folder-group">
      <div class="folder-label ${open?'open':''}" onclick="toggleFolder(${JSON.stringify(key)})">
        <span class="arrow">▶</span>
        <span class="folder-icon">${icon}</span>
        <span class="folder-name">${label}</span>
        <span class="folder-badge">${posts.length}</span>
      </div>
      <div class="folder-children" style="${open?'':'display:none'}">
        ${posts.map(p => `
          <div class="post-item ${currentFile===p.file?'active':''}"
               onclick="openPost(${JSON.stringify(p.file)})">
            <div class="post-item-title">${p.title}</div>
            <div class="post-item-date">${p.date}</div>
          </div>`).join('')}
      </div>
    </div>`;
  }

  document.getElementById('folder-tree').innerHTML = html ||
    '<div style="padding:12px;font-size:.78rem;color:var(--muted)">글이 없습니다</div>';
}

function toggleFolder(key) {
  if (expandedFolders.has(key)) expandedFolders.delete(key);
  else expandedFolders.add(key);
  renderFolderTree();
}

// ── folder select in editor ───────────────────────────────────────────────────
function updateFolderSelect(selectedFolder) {
  const sel = document.getElementById('post-folder');
  const current = selectedFolder !== undefined ? selectedFolder : sel.value;
  sel.innerHTML = '<option value="">(미분류)</option>';
  for (const f of allFolders) {
    const opt = document.createElement('option');
    opt.value = f.name;
    opt.textContent = `📁 ${f.name}`;
    sel.appendChild(opt);
  }
  sel.value = current;
}

function onFolderChange() {
  renderPreview();
}

// ── mode switching ────────────────────────────────────────────────────────────
function showPostPane() {
  document.getElementById('pane-post').style.display = '';
  document.getElementById('pane-homepage').style.display = 'none';
  document.getElementById('btn-homepage').classList.remove('active');
  mode = 'post';
}
function showHomepagePane() {
  document.getElementById('pane-post').style.display = 'none';
  document.getElementById('pane-homepage').style.display = '';
  document.getElementById('btn-homepage').classList.add('active');
  mode = 'homepage';
}

// ── new post / open post ──────────────────────────────────────────────────────
function newPost() {
  currentFile = null;
  showPostPane();
  document.getElementById('post-title').value = '';
  document.getElementById('post-body').value = '';
  document.getElementById('post-tags').value = '';
  document.getElementById('post-date').value = new Date().toISOString().slice(0,10);
  document.getElementById('post-math').checked = true;
  document.getElementById('editing-label').textContent = '새 글';
  renderFolderTree();
  renderPreview();
  setStatus('새 글 작성 중', '');
}

async function openPost(file) {
  currentFile = file;
  showPostPane();
  const r = await fetch('/api/post?file=' + encodeURIComponent(file));
  const data = await r.json();
  if (!data.ok) { setStatus('✗ 파일 읽기 실패', 'err'); return; }

  document.getElementById('post-title').value = data.title || '';
  document.getElementById('post-date').value  = data.date  || '';
  document.getElementById('post-tags').value  = data.tags  || '';
  document.getElementById('post-math').checked = data.math === 'true' || data.math === true;
  document.getElementById('post-body').value  = data.body  || '';
  document.getElementById('editing-label').textContent = file;

  // set folder from file path
  const parts = file.split('/');
  const folder = parts.length > 1 ? parts.slice(0,-1).join('/') : '';
  updateFolderSelect(folder);

  renderFolderTree();
  renderPreview();
  setStatus(`"${data.title}" 편집 중`, '');
}

async function promptNewFolder() {
  const name = prompt('새 폴더 이름:');
  if (!name || !name.trim()) return;
  setStatus('폴더 생성 중...');
  const res = await apiFetch('/api/create-folder', {name: name.trim()});
  if (res.ok) {
    await loadAll();
    setStatus(`✓ 폴더 "${name}" 생성됨`, 'ok');
  } else {
    setStatus('✗ ' + res.error, 'err');
  }
}

async function openHomepage() {
  showHomepagePane();
  const data = await fetch('/api/homepage').then(r => r.json());
  document.getElementById('hp-name').value = data.name || '';
  document.getElementById('hp-bio').value  = data.bio  || '';
  renderEduList(data.education || []);
  document.getElementById('preview-site-title').textContent = data.name || 'Lighton';
  renderPreview();
  setStatus('메인 페이지 편집 중', '');
}

// ── education entries ─────────────────────────────────────────────────────────
function renderEduList(entries) {
  eduEntries = entries;
  document.getElementById('edu-list').innerHTML = eduEntries.map((e, i) => `
    <div class="edu-entry">
      <div class="field"><label>학교</label>
        <input type="text" value="${e.school}"
          oninput="eduEntries[${i}].school=this.value;renderPreview()">
      </div>
      <div class="field" style="flex:1.4"><label>학위/전공</label>
        <input type="text" value="${e.degree}"
          oninput="eduEntries[${i}].degree=this.value;renderPreview()">
      </div>
      <div class="field"><label>기간</label>
        <input type="text" value="${e.period}"
          oninput="eduEntries[${i}].period=this.value;renderPreview()">
      </div>
      <button class="edu-del" onclick="delEdu(${i})">✕</button>
    </div>`).join('');
}

function addEduEntry() {
  eduEntries.push({school:'',degree:'',period:''});
  renderEduList(eduEntries);
  renderPreview();
}

function delEdu(i) {
  eduEntries.splice(i,1);
  renderEduList(eduEntries);
  renderPreview();
}

// ── markdown → html ───────────────────────────────────────────────────────────
function mdToHtml(md) {
  return md
    .replace(/\$\$([\s\S]*?)\$\$/g,  (_, m) => `<span class="mb">$$${m}$$</span>`)
    .replace(/\$([^\n$]+?)\$/g,       (_, m) => `<span class="mi">$${m}$</span>`)
    .replace(/^```[\w]*\n([\s\S]*?)^```/gm, '<pre><code>$1</code></pre>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,         '<em>$1</em>')
    .replace(/`([^`]+)`/g,         '<code>$1</code>')
    .replace(/^> (.+)$/gm,         '<blockquote>$1</blockquote>')
    .replace(/^---$/gm,            '<hr>')
    .replace(/^\- (.+)$/gm,        '<li>$1</li>')
    .replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2">$1</a>')
    .split(/\n\n+/)
    .map(b => {
      const t = b.trim();
      if (!t) return '';
      if (/^<(h[1-6]|pre|blockquote|hr|li|ul|ol|div)/.test(t)) return t;
      return `<p>${t}</p>`;
    }).join('\n')
    .replace(/<span class="mb">\$\$([\s\S]*?)\$\$<\/span>/g, (_, m) => `$$${m}$$`)
    .replace(/<span class="mi">\$([^$]*?)\$<\/span>/g,       (_, m) => `$${m}$`);
}

// ── preview renderer ──────────────────────────────────────────────────────────
function renderPreview() {
  if (mode === 'post')     renderPostPreview();
  else                     renderHomepagePreview();
}

function renderPostPreview() {
  const title  = document.getElementById('post-title').value;
  const date   = document.getElementById('post-date').value;
  const tags   = document.getElementById('post-tags').value;
  const body   = document.getElementById('post-body').value;
  const math   = document.getElementById('post-math').checked;
  const folder = document.getElementById('post-folder').value;

  const tagHtml = tags.split(',').map(t=>t.trim()).filter(Boolean)
    .map(t => `<span style="background:rgba(124,106,247,.18);padding:1px 7px;border-radius:4px">${t}</span>`)
    .join(' ');
  const folderBadge = folder
    ? `<span style="color:#7c6af7;font-size:.72rem">📁 ${folder}</span>` : '';

  const el = document.getElementById('preview-content');
  el.innerHTML = `
    <div class="pm-post-title">${title || '<span style="opacity:.3">제목 없음</span>'}</div>
    <div class="pm-post-meta">
      <span>📅 ${date}</span>
      ${tagHtml}
      ${folderBadge}
      ${math ? '<span style="color:rgba(94,234,212,.7);font-size:.72rem">∑ KaTeX</span>' : ''}
    </div>
    <div class="pm-post-body">${mdToHtml(body)}</div>`;

  if (math && window._katexReady) {
    renderMathInElement(el, {
      delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
      throwOnError: false
    });
  }
}

function renderHomepagePreview() {
  const name = document.getElementById('hp-name').value || 'Lighton';
  const bio  = document.getElementById('hp-bio').value  || '';
  document.getElementById('preview-site-title').textContent = name;

  const eduHtml = eduEntries.map(e => `
    <div class="pm-cv-row">
      <span><span class="pm-cv-school">${e.school}</span>
            <span class="pm-cv-deg">${e.degree}</span></span>
      <span class="pm-cv-period">${e.period}</span>
    </div>`).join('');

  // folder list for preview
  const folderHtml = allFolders.map(f => `
    <div class="pm-folder-item">
      <span class="pm-folder-item-name">📁 ${f.name}</span>
      <span class="pm-folder-item-count">${f.count}</span>
    </div>`).join('');

  const rootPosts = allPosts.filter(p => !p.folder);
  if (rootPosts.length) {
    // folderHtml += already shown in pm-folder-item above
  }

  const recentHtml = allPosts.slice(0,6).map(p => `
    <div class="pm-post-card">
      <div class="pm-card-title">${p.title}</div>
      <div class="pm-card-meta">${p.date}</div>
      ${p.folder ? `<div class="pm-card-folder">📁 ${p.folder}</div>` : ''}
    </div>`).join('');

  document.getElementById('preview-content').innerHTML = `
    <div class="pm-home-info">
      <h1>${name}</h1>
      <p>${bio.replace(/\n/g,'<br>')}</p>
      ${eduEntries.length ? `
        <hr class="pm-cv-divider">
        <div class="pm-cv-label">학력</div>
        ${eduHtml}` : ''}
    </div>
    <div class="pm-folder-layout">
      <div class="pm-folder-nav">
        <div class="pm-folder-nav-title">카테고리</div>
        ${folderHtml || '<div style="font-size:.78rem;color:rgba(255,255,255,.3)">폴더 없음</div>'}
        ${rootPosts.length ? `
          <div class="pm-folder-item">
            <span class="pm-folder-item-name">📄 미분류</span>
            <span class="pm-folder-item-count">${rootPosts.length}</span>
          </div>` : ''}
      </div>
      <div>
        <div class="pm-recent-title">최근 글</div>
        ${recentHtml || '<div style="font-size:.78rem;color:rgba(255,255,255,.3)">글 없음</div>'}
      </div>
    </div>`;
}

// ── save / push ───────────────────────────────────────────────────────────────
function setStatus(msg, type='') {
  const el = document.getElementById('status');
  el.textContent = msg; el.className = type;
}

function buildPostPayload() {
  const title  = document.getElementById('post-title').value || 'Untitled';
  const date   = document.getElementById('post-date').value;
  const folder = document.getElementById('post-folder').value;
  const tags   = document.getElementById('post-tags').value
    .split(',').map(t => t.trim()).filter(Boolean);
  const math   = document.getElementById('post-math').checked;
  const body   = document.getElementById('post-body').value;

  let fm = `---\ntitle: "${title}"\ndate: ${date}\n`;
  if (tags.length) fm += `tags: [${tags.map(t=>`"${t}"`).join(', ')}]\n`;
  if (math)        fm += `math: true\n`;
  fm += `---\n\n`;

  // slug from current filename or from title
  const slug = currentFile
    ? currentFile.split('/').pop().replace('.md','')
    : slugify(title);
  const newPath = folder ? `${folder}/${slug}` : slug;
  const oldPath = currentFile ? currentFile.replace('.md','') : null;

  return { content: fm + body, title, newPath, oldPath };
}

function slugify(t) {
  return t.toLowerCase()
    .replace(/[^\w가-힣\s-]/g,'')
    .replace(/\s+/g,'-')
    .replace(/-+/g,'-')
    .trim() || 'post';
}

async function apiFetch(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  return r.json();
}

async function saveCurrentFile() {
  if (mode === 'post') {
    const {content, title, newPath, oldPath} = buildPostPayload();
    setStatus('저장 중...');
    const res = await apiFetch('/api/save', {path: newPath, content,
      oldPath: oldPath !== newPath ? oldPath : null});
    if (res.ok) {
      currentFile = newPath + '.md';
      document.getElementById('editing-label').textContent = currentFile;
      setStatus(`✓ 저장됨`, 'ok');
      await loadAll();
    } else setStatus('✗ ' + res.error, 'err');
  } else {
    await saveHomepage();
  }
}

async function saveHomepage() {
  const name = document.getElementById('hp-name').value;
  const bio  = document.getElementById('hp-bio').value;
  setStatus('저장 중...');
  const res = await apiFetch('/api/save-homepage', {name, bio, education: eduEntries});
  if (res.ok) setStatus('✓ 홈페이지 저장됨', 'ok');
  else        setStatus('✗ ' + res.error, 'err');
}

async function pushCurrent() {
  if (mode === 'post') {
    const {content, title, newPath, oldPath} = buildPostPayload();
    setStatus('Push 중...');
    document.querySelectorAll('.btn').forEach(b => b.disabled = true);
    const res = await apiFetch('/api/push', {path: newPath, content, title,
      oldPath: oldPath !== newPath ? oldPath : null});
    document.querySelectorAll('.btn').forEach(b => b.disabled = false);
    if (res.ok) {
      currentFile = newPath + '.md';
      document.getElementById('editing-label').textContent = currentFile;
      const urlSlug = newPath.split('/').pop();
      setStatus(`✓ 배포됨 → lighton07.github.io/posts/${newPath}/`, 'ok');
      await loadAll();
    } else setStatus('✗ ' + res.error, 'err');
  } else {
    await saveHomepage();
    await _doSync('chore: update homepage');
  }
}

async function syncAll() {
  const msg = prompt('커밋 메시지:', 'chore: update blog');
  if (!msg) return;
  await _doSync(msg);
}

async function _doSync(msg) {
  setStatus('전체 동기화 중...');
  document.querySelectorAll('.btn').forEach(b => b.disabled = true);
  const res = await apiFetch('/api/sync', {message: msg});
  document.querySelectorAll('.btn').forEach(b => b.disabled = false);
  if (res.ok) setStatus('✓ 전체 변경사항 push됨', 'ok');
  else        setStatus('✗ ' + res.error, 'err');
}
</script>
</body>
</html>
"""

# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if   parsed.path == '/api/posts':    self._json(list_posts())
        elif parsed.path == '/api/folders':  self._json(list_folders())
        elif parsed.path == '/api/homepage': self._json(read_homepage())
        elif parsed.path == '/api/post':
            self._json(self._read_post(qs.get('file', [None])[0]))
        else:
            self._html(HTML)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        dispatch = {
            '/api/save':          self._save,
            '/api/push':          self._push,
            '/api/sync':          self._sync,
            '/api/save-homepage': self._save_homepage,
            '/api/create-folder': self._create_folder,
        }
        fn = dispatch.get(urlparse(self.path).path)
        self._json(fn(body) if fn else {"ok": False, "error": "unknown endpoint"})

    def _html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_post(self, filepath):
        if not filepath:
            return {"ok": False, "error": "no file"}
        path = POSTS_DIR / filepath
        if not path.exists():
            return {"ok": False, "error": "not found"}
        try:
            fm, body = parse_frontmatter(path.read_text(encoding='utf-8'))
            tags = fm.get('tags', '').strip('[]').replace('"', '')
            return {"ok": True, "file": filepath, "body": body,
                    "title": fm.get('title',''), "date": fm.get('date',''),
                    "tags": tags, "math": fm.get('math','false')}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _resolve_path(self, path_str):
        """path_str like 'math/foo' or 'hello' → (folder_dir, filename)"""
        parts = path_str.strip('/').split('/')
        filename = parts[-1] + '.md'
        if len(parts) > 1:
            folder_dir = POSTS_DIR / '/'.join(parts[:-1])
        else:
            folder_dir = POSTS_DIR
        return folder_dir, filename

    def _save(self, body):
        try:
            new_path = body['path']
            old_path = body.get('oldPath')
            folder_dir, filename = self._resolve_path(new_path)
            folder_dir.mkdir(parents=True, exist_ok=True)
            (folder_dir / filename).write_text(body['content'], encoding='utf-8')
            # move: delete old file
            if old_path and old_path != new_path:
                old_dir, old_file = self._resolve_path(old_path)
                old_filepath = old_dir / old_file
                if old_filepath.exists():
                    old_filepath.unlink()
            return {"ok": True, "path": new_path + '.md'}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _push(self, body):
        try:
            r = self._save(body)
            if not r['ok']: return r
            title = body.get('title', 'new post')
            run_git('add', '-A')
            st = subprocess.run(['git', 'status', '--porcelain'],
                                cwd=BLOG_DIR, capture_output=True, text=True)
            if not st.stdout.strip():
                return {"ok": True, "note": "nothing to commit"}
            run_git('commit', '-m', f'post: {title}')
            run_git('push')
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _save_homepage(self, body):
        try:
            write_homepage(body.get('name',''), body.get('bio',''),
                           body.get('education', []))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _create_folder(self, body):
        try:
            name = body.get('name', '').strip()
            if not name or '/' in name or '..' in name:
                return {"ok": False, "error": "invalid folder name"}
            folder = POSTS_DIR / name
            folder.mkdir(exist_ok=True)
            index = folder / '_index.md'
            if not index.exists():
                index.write_text(f'---\ntitle: "{name}"\n---\n', encoding='utf-8')
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _sync(self, body):
        try:
            run_git('add', '-A')
            st = subprocess.run(['git', 'status', '--porcelain'],
                                cwd=BLOG_DIR, capture_output=True, text=True)
            if not st.stdout.strip():
                return {"ok": True, "note": "nothing to commit"}
            run_git('commit', '-m', body.get('message', 'chore: update'))
            run_git('push')
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def main():
    port   = 8787
    server = http.server.HTTPServer(('127.0.0.1', port), Handler)
    url    = f'http://localhost:{port}'
    print(f'Blog Editor -> {url}  (Ctrl+C to stop)')
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')

if __name__ == '__main__':
    main()
