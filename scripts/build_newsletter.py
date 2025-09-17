#!/usr/bin/env python3
import re, html, shutil
from pathlib import Path
from urllib.parse import urlparse

DIGEST_MD = Path("/Users/sujataavirneni/RESUME-2025/news_markdown_digests/digest_5bullets.md")
SITE_ROOT = Path("docs")
ART_DIR   = SITE_ROOT / "articles"
CSS_FILE  = SITE_ROOT / "style.css"

SITE_ROOT.mkdir(parents=True, exist_ok=True)
ART_DIR.mkdir(parents=True, exist_ok=True)

def slugify(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return (s[:max_len] or "item").strip("-")

def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.","")
    except Exception:
        return ""

def parse_digest(md_path: Path):
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    items = []
    title = None
    bullets = []
    source = ""
    iso = ""

    H = re.compile(r"^#{2,3}\s+(.*)")
    B = re.compile(r"^\s*-\s+(.*)")          # already prefixed with "-"
    SRC = re.compile(r"\[Source\]\((.*?)\)")
    ISO = re.compile(r"·\s*([0-9T:\-\+Z:]+)")

    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = H.match(line)
        if m:
            if title:
                items.append({"title": title, "bullets": bullets, "source": source, "iso": iso})
            title = m.group(1).strip()
            bullets, source, iso = [], "", ""
            continue
        if title:
            mb = B.match(line)
            if mb:
                bullets.append(mb.group(1).strip())
                continue
            if "[Source](" in line:
                ms = SRC.search(line)
                mi = ISO.search(line)
                source = ms.group(1) if ms else ""
                iso = mi.group(1) if mi else ""
    if title:
        items.append({"title": title, "bullets": bullets, "source": source, "iso": iso})
    return items

BASE_CSS = """
:root{--bg:#0b0c10;--card:#16181d;--text:#e6e6e6;--muted:#a0a7b4;--accent:#58a6ff;}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu; background:var(--bg); color:var(--text);}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.container{max-width:900px;margin:0 auto;padding:24px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.card{background:var(--card);border-radius:16px;padding:20px;margin:16px 0;box-shadow:0 2px 12px rgba(0,0,0,.25)}
.badge{display:inline-block;background:#222633;color:var(--muted);padding:4px 10px;border-radius:20px;font-size:12px;margin-right:8px}
ul{line-height:1.45}
.footer{color:var(--muted);margin-top:40px;font-size:14px}
.btn{display:inline-block;background:var(--accent);color:#081018;padding:8px 14px;border-radius:10px;font-weight:600}
"""

def write_css():
    CSS_FILE.write_text(BASE_CSS, encoding="utf-8")

def article_html(it, slug):
    title = html.escape(it["title"])
    src = it.get("source","")
    iso = it.get("iso","")
    dom = domain_of(src) if src else ""
    bullets_li = "\n".join(f"<li>{html.escape(b)}</li>" for b in it.get("bullets",[]) )
    src_html = f'<a href="{html.escape(src)}" target="_blank" rel="noopener nofollow">{html.escape(dom or "Original")}</a>' if src else "Original"
    tweet_text = title + "\\n" + "\\n".join([("• " + b) for b in it.get("bullets",[])[:7]])
    tweet_url = "https://twitter.com/intent/tweet?text=" + html.escape(tweet_text)

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="stylesheet" href="/newsletter/style.css"/>
<title>{title} — Newsletter</title>
</head><body>
<div class="container">
  <div class="header">
    <h1 style="margin:0;font-size:28px">Newsletter</h1>
    <a class="btn" href="/newsletter/">Home</a>
  </div>
  <div class="card">
    <h2 style="margin-top:0">{title}</h2>
    <div class="badge">{html.escape(iso) if iso else ""}</div>
    <ul>
      {bullets_li}
    </ul>
    <p>
      <a class="btn" href="{tweet_url}" target="_blank" rel="noopener">Tweet bullets</a>
      &nbsp;&nbsp;
      {src_html}
    </p>
  </div>
  <div class="footer">Built from digest_5bullets.md</div>
</div>
</body></html>"""

def index_html(items):
    cards = []
    for it in items:
        slug = slugify(it["title"])
        dom = domain_of(it.get("source",""))
        date = html.escape(it.get("iso",""))
        cards.append(f"""
        <div class="card">
          <h3 style="margin-top:0"><a href="/newsletter/articles/{slug}/">{html.escape(it['title'])}</a></h3>
          <div class="badge">{date}</div>
          <p style="margin:8px 0;color:var(--muted)">{html.escape(dom) if dom else ""}</p>
          <ul>
            { "".join(f"<li>{html.escape(b)}</li>" for b in it.get("bullets",[])[:3]) }
          </ul>
          <p><a href="/newsletter/articles/{slug}/">Read full bullets →</a></p>
        </div>""")
    body = "\n".join(cards) or "<p>No articles found.</p>"
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="stylesheet" href="/newsletter/style.css"/>
<title>Newsletter</title>
</head><body>
<div class="container">
  <div class="header">
    <h1 style="margin:0">Newsletter</h1>
    <a class="btn" href="https://github.com/suavir600/newsletter" target="_blank" rel="noopener">GitHub</a>
  </div>
  {body}
  <div class="footer">GitHub Pages • docs/ folder • static HTML</div>
</div>
</body></html>"""

def build():
    items = parse_digest(DIGEST_MD)
    write_css()
    # Clear old article pages (optional)
    for p in ART_DIR.glob("*"):
        if p.is_dir():
            shutil.rmtree(p)
    # Write article pages
    for it in items:
        slug = slugify(it["title"])
        out_dir = ART_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(article_html(it, slug), encoding="utf-8")
    # Write home
    (SITE_ROOT / "index.html").write_text(index_html(items), encoding="utf-8")
    print(f"Built {len(items)} article page(s) into {SITE_ROOT}/")

if __name__ == "__main__":
    build()
