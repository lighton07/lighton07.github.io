import subprocess
from .config import BLOG_DIR


def run(*cmd):
    r = subprocess.run(["git"] + list(cmd), cwd=BLOG_DIR,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()


def has_changes():
    r = subprocess.run(["git", "status", "--porcelain"],
                       cwd=BLOG_DIR, capture_output=True, text=True)
    return bool(r.stdout.strip())


def commit_and_push(message):
    run("add", "-A")
    if not has_changes():
        return {"ok": True, "note": "nothing to commit"}
    run("commit", "-m", message)
    run("push")
    return {"ok": True}
