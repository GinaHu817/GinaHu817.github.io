#!/usr/bin/env python3
"""Publish a paper-notes blog post to GinaHu817.github.io.

Usage:
    python3 scripts/publish.py PATH/TO/post.html [--slug SLUG] [--date YYYY-MM-DD]
                                                 [--paper-url URL] [--no-push]

What it does:
  1. Pulls the post content out of the HTML (works with Claude artifact exports,
     which wrap the post in a big <div id="vis-container"> with app CSS).
  2. Wraps it in the site template -> posts/<slug>.html
  3. Records it in posts.json and rebuilds index.html
  4. git commit + push (GitHub Pages redeploys automatically)

Re-publishing the same slug replaces the old version.
"""
import argparse
import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
INDEX_JSON = ROOT / "posts.json"
SITE_TITLE = "Gina's Paper Notes"
SITE_TAGLINE = "Notes and reflections on the papers I read."


def text_of(fragment):
    """Strip tags and collapse whitespace."""
    t = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def find_class(src, cls):
    m = re.search(rf'<div class="{cls}">(.*?)</div>', src, re.S)
    return text_of(m.group(1)) if m else ""


def extract_content(src):
    """Return the inner post HTML (its own <style> blocks + markup)."""
    m = re.search(r'<div id="vis-container">(.*)</div>\s*</body>', src, re.S)
    if m:  # Claude artifact export
        inner = m.group(1)
    else:
        m = re.search(r"<body[^>]*>(.*)</body>", src, re.S)
        inner = m.group(1) if m else src
    # drop stray <meta> tags that sit inside the body
    inner = re.sub(r"<meta[^>]*>", "", inner)
    return inner.strip()


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[\s_-]+", "-", s).strip("-")[:60]


POST_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<meta name="description" content="{description}">
<style>
  .site-nav {{ max-width: 680px; margin: 0 auto 28px; font-family: system-ui, sans-serif; font-size: 13px; }}
  .site-nav a {{ color: #4361ee; text-decoration: none; }}
  .site-nav a:hover {{ text-decoration: underline; }}
  .paper-link {{ max-width: 680px; margin: 0 auto 0; font-family: system-ui, sans-serif; font-size: 13px; }}
</style>
</head>
<body>
<nav class="site-nav"><a href="../index.html">&larr; All paper notes</a></nav>
{content}
{paper_link}
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{site}</title>
<meta name="description" content="{tagline}">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #fafaf8; font-family: Georgia, serif; color: #1a1a1a; padding: 56px 20px; }}
  .wrap {{ max-width: 680px; margin: 0 auto; }}
  header {{ margin-bottom: 40px; padding-bottom: 24px; border-bottom: 1px solid #e5e5e5; }}
  h1 {{ font-size: 34px; margin-bottom: 10px; color: #111; }}
  .tagline {{ font-size: 17px; color: #555; font-style: italic; }}
  .links {{ margin-top: 14px; font-family: system-ui, sans-serif; font-size: 13px; }}
  .links a {{ color: #4361ee; text-decoration: none; margin-right: 14px; }}
  .post {{ display: block; text-decoration: none; color: inherit; padding: 22px 0; border-bottom: 1px solid #eee; }}
  .post:hover h2 {{ color: #4361ee; }}
  .tag {{ font-family: system-ui, sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
          text-transform: uppercase; color: #4361ee; margin-bottom: 8px; }}
  h2 {{ font-size: 22px; line-height: 1.3; margin-bottom: 8px; color: #111; transition: color .15s; }}
  .sub {{ font-size: 16px; color: #555; line-height: 1.55; margin-bottom: 8px; }}
  .meta {{ font-family: system-ui, sans-serif; font-size: 12px; color: #999; }}
  .empty {{ color: #888; font-style: italic; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{site}</h1>
    <p class="tagline">{tagline}</p>
    <div class="links"><a href="https://github.com/GinaHu817">GitHub</a></div>
  </header>
  <main>
{items}
  </main>
</div>
</body>
</html>
"""

ITEM_TEMPLATE = """    <a class="post" href="posts/{slug}.html">
      <div class="tag">{tag}</div>
      <h2>{title}</h2>
      <p class="sub">{subtitle}</p>
      <div class="meta">{date_display}</div>
    </a>"""


def build_index(posts):
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)
    items = "\n".join(
        ITEM_TEMPLATE.format(**{k: html.escape(str(v)) for k, v in p.items()})
        for p in posts
    ) or '    <p class="empty">No posts yet.</p>'
    (ROOT / "index.html").write_text(
        INDEX_TEMPLATE.format(site=SITE_TITLE, tagline=SITE_TAGLINE, items=items)
    )


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", nargs="?", help="post HTML file (omit with --rebuild)")
    ap.add_argument("--slug", help="URL name, default: from the title")
    ap.add_argument("--date", help="YYYY-MM-DD, default: today")
    ap.add_argument("--paper-url", help="link to the original paper (e.g. arXiv)")
    ap.add_argument("--no-push", action="store_true", help="build + commit locally only")
    ap.add_argument("--rebuild", action="store_true", help="just rebuild index.html from posts.json")
    a = ap.parse_args()

    posts = json.loads(INDEX_JSON.read_text()) if INDEX_JSON.exists() else []

    if a.rebuild:
        build_index(posts)
        print("Rebuilt index.html")
        return
    if not a.html:
        ap.error("html file is required")

    src = Path(a.html).expanduser().read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", src, re.S)
    title = text_of(h1.group(1)) if h1 else Path(a.html).stem.replace("_", " ").title()
    subtitle = find_class(src, "subtitle")
    tag = find_class(src, "tag") or "Paper Notes"
    meta = find_class(src, "meta")
    date = a.date or dt.date.today().isoformat()
    slug = a.slug or slugify(title)

    paper_link = (
        f'<p class="paper-link">Original paper: <a href="{html.escape(a.paper_url)}">{html.escape(a.paper_url)}</a></p>'
        if a.paper_url else ""
    )
    POSTS_DIR.mkdir(exist_ok=True)
    (POSTS_DIR / f"{slug}.html").write_text(POST_TEMPLATE.format(
        title=html.escape(title), site=SITE_TITLE,
        description=html.escape(subtitle or title),
        content=extract_content(src), paper_link=paper_link,
    ))

    entry = {
        "slug": slug, "title": title, "subtitle": subtitle, "tag": tag, "date": date,
        "date_display": meta or dt.date.fromisoformat(date).strftime("%B %Y"),
    }
    posts = [p for p in posts if p["slug"] != slug] + [entry]
    INDEX_JSON.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n")
    build_index(posts)
    print(f"Built posts/{slug}.html  ({title})")

    git("add", "-A")
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode == 0:
        print("Nothing changed; skipping commit.")
        return
    git("commit", "-m", f"Post: {title}")
    if not a.no_push:
        git("push")
        print(f"Live in ~1 min at https://ginahu817.github.io/posts/{slug}.html")


if __name__ == "__main__":
    sys.exit(main())
