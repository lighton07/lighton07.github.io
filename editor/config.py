from pathlib import Path

BLOG_DIR  = Path(__file__).parent.parent      # my-blog/
POSTS_DIR = BLOG_DIR / "content" / "posts"
HUGO_TOML = BLOG_DIR / "hugo.toml"
HOME_INFO = BLOG_DIR / "layouts" / "partials" / "home_info.html"
