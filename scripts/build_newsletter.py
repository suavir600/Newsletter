#!/usr/bin/env python3
import re, os, html, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ---- CONFIG ----
DIGEST_FILE = Path("/Users/sujataavirneni/RESUME-2025/news_markdown_digests/digest_5bullets.md")
OUT_DIR     = Path("docs")                     # GitHub Pages root
ART_DIR     = OUT_DIR / "articles"             # per-article folders
SITE_TITLE  = "Daily Finance Newsletter"
SITE_DESC   = "5–7 key bullets per story"
SITE_URL    = "https://suavir600.github.io/newsletter"

OUT_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR.mkdir(parents=True, exist_ok=True)

# ---- Parsers ----
H_RE   = re.compile(r"^#{2,3}\s+(.*)")
B_RE   = re.compile(r"^\s*[-*•]\s+(.*)")
SRC_RE = re.compile(r"\[Source\]\((.*?)\)")
ISO_RE = re.compile(r"·\s*([0-9T:\-\+Z:]+)")
ORIG_RE = re.compile(r"\[Original\]\((.*?)\)")

def slugify(s: str, max_len=80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return (s[:max_len] or "item")

def read_digest(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Digest not found: {path}")
    return path.read_text(encoding="utf-8").splitlines()

def parse_items(lines):
    items, cur = [], None
    for line in lines:
        m = H_RE.match(line)
        if m:
            if cur: items.append(cur)
            title = m.group(1).strip()
            cur = {"title": title, "bullets": [], "original_url": "", "iso": "", "slug": slugify(title)}
            continue
        if cur:
            mb = B_RE.match(line)
            if mb:
                cur["bullets"].append(mb.group(1).strip())
                continue
            if "[Source](" in line:
                ms = SRC_RE.search(line)
                mo = ORIG_RE.search(line)
                cur["source_url"] = ms.group(1) if ms else ""
                cur["original_url"] = mo.group(1) if mo else cur.get("source_url","")
                mi = ISO_RE.search(line)
                cur["iso"] = mi.group(1) if mi else ""
    if cur:
        items.append(cur)
    return items

def tweet_intent(title: str, bullets: list[str], url: str=""):
    # Compact 280-char tweet (reserve for URL)
    parts = [title.strip()] + [f"• {b.strip()}" for b in (bullets or [])[:7]]
    reserve = 25 if url else 0
    out, MAX = "", 280 - reserve
    for p in parts:
        cand = (out + ("\n" if out else "") + p)
        if len(cand) <= MAX:
            out = cand
        else:
            room = MAX - len(out) - (1 if out else 0)
            if room > 3:
                out = out + ("\n" if out else "") + p[:room-1] + "…"
            break
    if url:
        out = (out + "\n" + url).strip()
    return "https://twitter.com/intent/tweet?text=" + urllib.parse.quote_plus(out)

# ---- HTML templates ----
CSS = """
:root{--bg:#0b0f19;--fg:#e8ecf2;--muted:#93a1b1;--card:#121826;--accent:#4f8cff}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.container{max-width:980px;margin:0 auto;padding:20px}
.nav{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.brand{font-weight:700} .muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 6px 20px rgba(0,0,0,.25)}
.card h3{margin:0 0 8px 0;font-size:1.05rem}
.badge{display:inline-block;background:#1c2335;color:#c0cad8;padding:.2rem .5rem;border-radius:999px;font-size:.75rem;margin-right:.4rem}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:.5rem .75rem;border-radius:10px;font-weight:600}
.btn-outline{background:transparent;border:1px solid var(--accent);color:var(--accent)}
.list ul{margin:.5rem 0 0 1.2rem}
.footer{margin-top:36px;color:var(--muted);font-size:.9rem;text-align:center}
hr{border:none;border-top:1px solid #223; margin:16px 0}
"""

def layout_html(title, body, description=""):
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description or SITE_DESC)}" />
    <link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="{SITE_URL}/feed.xml" />
    <style>{CSS}</style>
  </head>
  <body>
    <div class="container">
      <div class="nav">
        <div class="brand"><a href="{SITE_URL}">{html.escape(SITE_TITLE)}</a></div>
        <div class="muted">{html.escape(SITE_DESC)}</div>
      </div>
      {body}
      <div class="footer">© {datetime.now().year} · Built from digest_5bullets.md</div>
    </div>
  </body>
</html>"""

def article_card(it):
    href = f"{SITE_URL}/articles/{it['slug']}/"
    date_txt = (it.get("iso") or "").replace("T"," ").replace("Z"," UTC")
    src = it.get("original_url") or it.get("source_url") or "#"
    return f"""
<div class="card">
  <h3><a href="{href}">{html.escape(it['title'])}</a></h3>
  <div class="muted">{html.escape(date_txt)}</div>
  <div class="list"><ul>
    {''.join(f'<li>{html.escape(b)}</li>' for b in (it['bullets'][:5] if it.get('bullets') else []))}
  </ul></div>
  <div style="margin-top:.6rem">
    <a class="btn-outline" href="{src}" target="_blank" rel="noopener">Original</a>
    <a class="btn" href="{href}">Read</a>
  </div>
</div>
"""

def article_page_html(it):
    src = it.get("original_url") or it.get("source_url") or "#"
    date_txt = (it.get("iso") or "").replace("T"," ").replace("Z"," UTC")
    share = tweet_intent(it["title"], it.get("bullets") or [], f"{SITE_URL}/articles/{it['slug']}/")
    body = f"""
<h1>{html.escape(it['title'])}</h1>
<div class="muted">{html.escape(date_txt)}</div>
<hr />
<div class="list"><ul>
  {''.join(f'<li>{html.escape(b)}</li>' for b in (it.get('bullets') or []))}
</ul></div>
<div style="margin-top:12px">
  <a class="btn-outline" href="{src}" target="_blank" rel="noopener">Original</a>
  <a class="btn" href="{share}" target="_blank" rel="noopener">Share on X</a>
</div>
"""
    return layout_html(it["title"], body, description="; ".join(it.get("bullets", [])[:3]))

def index_html(items):
    cards = "\n".join(article_card(it) for it in items)
    body = f"""
<h1>Latest</h1>
<div class="grid">{cards}</div>
"""
    return layout_html(SITE_TITLE, body, SITE_DESC)

def rss_xml(items):
    now_iso = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items_xml = []
    for it in items:
        url = f"{SITE_URL}/articles/{it['slug']}/"
        desc = html.escape("; ".join(it.get("bullets", [])[:3]))
        pub = it.get("iso") or datetime.now(timezone.utc).isoformat()
        items_xml.append(f"""
  <item>
    <title>{html.escape(it['title'])}</title>
    <link>{url}</link>
    <guid>{url}</guid>
    <pubDate>{now_iso}</pubDate>
    <description><![CDATA[{desc}]]></description>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{html.escape(SITE_TITLE)}</title>
  <link>{SITE_URL}</link>
  <description>{html.escape(SITE_DESC)}</description>
  <lastBuildDate>{now_iso}</lastBuildDate>
  {''.join(items_xml)}
</channel>
</rss>
"""

# ---- Build ----
def main():
    lines = read_digest(DIGEST_FILE)
    items = parse_items(lines)
    if not items:
        print("No items parsed — check digest format.")
        return

    # write index
    (OUT_DIR / "index.html").write_text(index_html(items), encoding="utf-8")

    # write articles
    for it in items:
        apath = ART_DIR / it["slug"] / "index.html"
        apath.parent.mkdir(parents=True, exist_ok=True)
        apath.write_text(article_page_html(it), encoding="utf-8")

    # write rss
    (OUT_DIR / "feed.xml").write_text(rss_xml(items), encoding="utf-8")

    print(f"Built {len(items)} articles into {OUT_DIR}/")

if __name__ == "__main__":
    main()
