# Gina's Paper Notes blog (GinaHu817.github.io)

Static GitHub Pages site. Live at https://ginahu817.github.io

## Posting a new paper blog
When the user says "post my blog" / gives a new HTML file (usually in ~/Desktop/paper/):
1. Run: `python3 scripts/publish.py <path/to/post.html> --paper-url <arXiv or paper link>`
   - Always pass a short `--slug` (e.g. `bert`, `attention-is-all-you-need`); add `--date YYYY-MM-DD` if not today.
   - Use `--no-push` to preview first, then open `posts/<slug>.html` / `index.html` in a browser.
2. The script extracts the post from Claude artifact exports, wraps it in the site template,
   updates `posts.json` + `index.html`, commits, and pushes. Pages redeploys in ~1 min.
3. Report the live URL to the user.

## Notes
- Do not commit paper PDFs (copyright) — link to the paper instead.
- Post HTML is expected to use: `.tag`, `<h1>`, `.subtitle`, `.meta` (these feed the index card).
- To edit the home page layout, change `INDEX_TEMPLATE` in `scripts/publish.py` then run
  `python3 scripts/publish.py --rebuild`.
