import re
from pathlib import Path
from .config import POSTS_DIR


def norm(p):
    return str(p).replace('\\', '/')


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


def read(filepath):
    path = POSTS_DIR / filepath
    if not path.exists():
        return None
    try:
        fm, body = parse_frontmatter(path.read_text(encoding='utf-8'))
        return {
            "file": filepath,
            "body": body,
            "title": fm.get('title', ''),
            "date":  fm.get('date', ''),
            "tags":  fm.get('tags', '').strip('[]').replace('"', ''),
            "math":  fm.get('math', 'false'),
        }
    except Exception:
        return None


def save(path_str, content, old_path_str=None):
    """Save post to path_str (without .md). If old_path_str differs, delete it (move)."""
    parts = path_str.strip('/').split('/')
    filename = parts[-1] + '.md'
    folder_dir = POSTS_DIR / '/'.join(parts[:-1]) if len(parts) > 1 else POSTS_DIR
    folder_dir.mkdir(parents=True, exist_ok=True)
    (folder_dir / filename).write_text(content, encoding='utf-8')

    if old_path_str and old_path_str != path_str:
        old_parts = old_path_str.strip('/').split('/')
        old_fn = old_parts[-1] + '.md'
        old_dir = POSTS_DIR / '/'.join(old_parts[:-1]) if len(old_parts) > 1 else POSTS_DIR
        old_fp = old_dir / old_fn
        if old_fp.exists():
            old_fp.unlink()

    return path_str + '.md'
