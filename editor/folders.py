import shutil
from pathlib import Path
from .config import POSTS_DIR
from .posts import norm, parse_frontmatter


def build_tree():
    """Return nested tree: {children: [{type, ...}, ...]}"""
    if not POSTS_DIR.exists():
        return {"children": []}
    return _node(POSTS_DIR, '')


def _node(dir_path, rel_path):
    children = []

    # Subdirectories first (folders)
    for d in sorted(dir_path.iterdir()):
        if not d.is_dir():
            continue
        child_rel = (rel_path + '/' + d.name).lstrip('/')
        sub = _node(d, child_rel)
        children.append({
            "type":     "folder",
            "name":     d.name,
            "path":     child_rel,
            "children": sub["children"],
        })

    # Files (posts), newest first, skip _index.md
    for f in sorted(dir_path.glob("*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name == '_index.md':
            continue
        file_rel = (rel_path + '/' + f.name).lstrip('/')
        try:
            fm, _ = parse_frontmatter(f.read_text(encoding='utf-8'))
            children.append({
                "type":   "post",
                "file":   file_rel,
                "folder": rel_path,
                "title":  fm.get("title", f.stem),
                "date":   fm.get("date", ""),
            })
        except Exception:
            children.append({"type": "post", "file": file_rel,
                              "folder": rel_path, "title": f.stem, "date": ""})

    return {"children": children}


def list_flat():
    """Flat list of {name, count} for the folder selector."""
    result = []
    if POSTS_DIR.exists():
        for d in sorted(POSTS_DIR.rglob("*")):
            if d.is_dir():
                count = len([f for f in d.glob("*.md") if f.name != "_index.md"])
                result.append({"name": norm(d.relative_to(POSTS_DIR)), "count": count})
    return result


def create(folder_path):
    name = folder_path.strip('/')
    if not name or '..' in name:
        raise ValueError("invalid folder path")
    folder = POSTS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    index = folder / '_index.md'
    if not index.exists():
        leaf = Path(name).name
        index.write_text(f'---\ntitle: "{leaf}"\n---\n', encoding='utf-8')
    return norm(folder.relative_to(POSTS_DIR))


def move_post(from_path, to_parent):
    from_file = POSTS_DIR / from_path
    if not from_file.exists():
        raise FileNotFoundError(f"post not found: {from_path}")
    filename = Path(from_path).name
    to_dir = POSTS_DIR / to_parent if to_parent else POSTS_DIR
    to_dir.mkdir(parents=True, exist_ok=True)
    to_file = to_dir / filename
    if from_file == to_file:
        return norm(to_file.relative_to(POSTS_DIR))
    from_file.rename(to_file)
    return norm(to_file.relative_to(POSTS_DIR))


def move_folder(from_path, to_parent):
    from_dir = POSTS_DIR / from_path
    if not from_dir.exists():
        raise FileNotFoundError(f"folder not found: {from_path}")
    folder_name = Path(from_path).name
    to_dir = POSTS_DIR / to_parent / folder_name if to_parent else POSTS_DIR / folder_name
    if from_dir == to_dir:
        return norm(to_dir.relative_to(POSTS_DIR))
    if to_dir.exists():
        raise FileExistsError(f"target already exists: {to_dir}")
    if str(to_dir).startswith(str(from_dir) + '/') or str(to_dir) == str(from_dir):
        raise ValueError("cannot move folder into itself")
    shutil.move(str(from_dir), str(to_dir))
    return norm(to_dir.relative_to(POSTS_DIR))
