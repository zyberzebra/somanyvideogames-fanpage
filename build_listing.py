#!/usr/bin/env python3
"""Build episode listing with formatted descriptions (no games, no RAWG)."""

import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
import html, re, json, ssl, time, os

RSS_URL = "https://gamecritics.com/category/podcasts/so-videogames/feed/"
NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
ctx = ssl._create_unverified_context()

EXPECTED_EPISODES = 486

months = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
          "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}

SAFE_TAGS = {"p","br","b","i","em","strong","a","ul","ol","li","u","s",
             "blockquote","cite","code","pre","hr","sub","sup","span","div",
             "h1","h2","h3","h4","h5","h6","dl","dt","dd"}

def sanitize(raw):
    if not raw:
        return ""
    raw = html.unescape(raw)
    raw = re.sub(r'<(script|style|iframe|object|embed|form|input|textarea|select|option|noscript)[^>]*>.*?</\1>', '', raw, flags=re.IGNORECASE|re.DOTALL)
    raw = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'</?([a-zA-Z][a-zA-Z0-9]*)[^>]*>', lambda m: m.group(0) if m.group(1).lower() in SAFE_TAGS else '', raw)
    raw = re.sub(r'<p>\s*</p>', '', raw)
    return raw.strip()

def fetch_rss():
    eps = []
    seen = set()
    page = 0
    while True:
        try:
            with urllib.request.urlopen(f"{RSS_URL}?paged={page}", context=ctx) as resp:
                root = ET.fromstring(resp.read())
        except Exception:
            break
        items = root.findall(".//item")
        if not items:
            break
        for item in items:
            url = item.findtext("link", "")
            if url in seen:
                continue
            seen.add(url)
            content_el = item.find("content:encoded", NS)
            desc = sanitize(content_el.text if content_el is not None else item.findtext("description", ""))
            desc = re.sub(r'\s*<p>\s*The post\s+.*?appeared first on\s+.*?\.?\s*</p>\s*', '', desc, flags=re.IGNORECASE)
            desc = desc.strip()
            pub_date = item.findtext("pubDate", "")
            date = ""
            if pub_date:
                parts = pub_date.split()
                if len(parts) >= 4:
                    date = f"{parts[3]}-{months.get(parts[2],'00')}-{parts[1].zfill(2)}"
            eps.append({
                "title": item.findtext("title", ""),
                "desc": desc,
                "date": date,
                "url": url,
            })
        print(f"  RSS page {page}: {len(items)} items ({len(eps)} unique)")
        page += 1
        time.sleep(0.5)
    return eps

def generate_html(eps):
    eps.sort(key=lambda e: e.get("date", ""), reverse=True)
    data_json = json.dumps(eps)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>So Videogames Podcast – Episodes</title>
<style>
:root {{
  color-scheme: dark;
  --bg: #111;
  --fg: #ccc;
  --border: #2a2a2a;
  --link: #7cb4f7;
  --muted: #777;
  --tog: #888;
  --mark-bg: #554400;
  --card-bg: #181818;
}}
.light {{
  color-scheme: light;
  --bg: #fff;
  --fg: #222;
  --border: #ddd;
  --link: #1a0dab;
  --muted: #888;
  --tog: #666;
  --mark-bg: #ffe066;
  --card-bg: #fafafa;
}}
* {{ box-sizing: border-box; }}
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 1rem; background: var(--bg); color: var(--fg); }}
h1 {{ font-size: 1.5rem; }}
#search {{ width: 100%; padding: 0.75rem; font-size: 1.2rem; margin-bottom: 0.5rem; box-sizing: border-box; background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; }}
.ep {{ margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
.ep-title {{ font-size: 1.1rem; font-weight: bold; }}
.ep-title a {{ color: var(--link); text-decoration: none; }}
.ep-title a:hover {{ text-decoration: underline; }}
.ep-date {{ color: var(--muted); font-size: 0.85rem; margin: 0.15rem 0 0.5rem 0; }}
.desc {{ margin-top: 0.4rem; font-size: 0.9rem; line-height: 1.6; display: none; overflow-wrap: break-word; }}
.desc.vis {{ display: block; }}
.desc p {{ margin: 0.5em 0; }}
.desc ul, .desc ol {{ margin: 0.3em 0; padding-left: 1.5rem; }}
.desc li {{ margin: 0.15em 0; }}
.desc a {{ color: var(--link); }}
.tog {{ color: var(--tog); cursor: pointer; font-size: 0.85rem; user-select: none; }}
.tog:hover {{ text-decoration: underline; color: var(--fg); }}
.meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
mark {{ background: var(--mark-bg); color: inherit; }}
.footer {{ margin-top: 2rem; font-size: 0.8rem; color: var(--muted); text-align: center; }}
.footer a {{ color: var(--link); }}
.header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }}
#theme {{ background: none; border: 1px solid var(--border); color: var(--fg); cursor: pointer; font-size: 0.9rem; padding: 0.3rem 0.6rem; border-radius: 5px; white-space: nowrap; }}
#theme:hover {{ background: var(--card-bg); }}
</style>
</head>
<body>
<div class="header">
  <h1>So Videogames Podcast – Episodes</h1>
  <button id="theme">☀ Light</button>
</div>
<input type="text" id="search" placeholder="Search titles and descriptions…" autofocus>
<p class="meta" id="count"></p>
<div id="results"></div>
<div class="footer">{len(eps)} / {EXPECTED_EPISODES} episodes · data from <a href="https://gamecritics.com/category/podcasts/so-videogames/">gamecritics.com</a></div>
<script>
const episodes = {data_json};

(function initTheme() {{
  const t = document.getElementById('theme');
  if (localStorage.getItem('theme') === 'light') {{
    document.documentElement.classList.add('light');
    t.textContent = '☾ Dark';
  }}
  t.onclick = function() {{
    document.documentElement.classList.toggle('light');
    const isLight = document.documentElement.classList.contains('light');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    t.textContent = isLight ? '☾ Dark' : '☀ Light';
  }};
}})();

function filter() {{
  const q = document.getElementById('search').value.toLowerCase().trim();
  const r = document.getElementById('results');
  let f = q ? episodes.filter(e => (e.title.toLowerCase().includes(q) || (e.desc && e.desc.toLowerCase().includes(q)))) : episodes;
  document.getElementById('count').textContent = f.length + ' / {EXPECTED_EPISODES} episodes';
  r.innerHTML = f.length ? f.map(e => epHTML(e, q)).join('') : '<p style="color:#888">No matches</p>';
}}

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function epHTML(e, q) {{
  const tid = 'd' + e.url.replace(/[^a-zA-Z0-9]/g, '');
  const title = hl(esc(e.title), esc(q));
  let desc = e.desc || '';
  const inDesc = q && desc.toLowerCase().includes(q);
  const vis = q && !e.title.toLowerCase().includes(q) && inDesc;
  const hlDesc = q ? hlDescText(desc, q) : desc;
  return '<div class="ep"><div class="ep-title"><a href="' + e.url + '" target="_blank">' + title + '</a></div>'
    + '<div class="ep-date">' + e.date + '</div>'
    + (desc ? '<div id="' + tid + '" class="desc' + (vis ? ' vis' : '') + '">' + hlDesc + '</div>' : '')
    + (desc ? '<div class="tog" onclick="var d=document.getElementById(\\'' + tid + '\\');d.classList.toggle(\\'vis\\');this.textContent=d.classList.contains(\\'vis\\')?\\'▾ Hide\\':\\'▸ Show\\'">' + (vis ? '▾ Hide' : '▸ Show') + '</div>' : '')
    + '</div>';
}}

function hl(t, q) {{
  if (!q) return t;
  try {{ return t.replace(new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'), '<mark class="hi">$1</mark>'); }}
  catch(e) {{ return t; }}
}}

function hlDescText(html, q) {{
  if (!q) return html;
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  walkText(tmp, q);
  return tmp.innerHTML;
}}

function walkText(node, q) {{
  if (node.nodeType === 3) {{
    const txt = node.textContent;
    if (txt.toLowerCase().includes(q)) {{
      const span = document.createElement('span');
      span.innerHTML = hl(esc(txt), esc(q));
      node.parentNode.replaceChild(span, node);
    }}
  }} else {{
    for (let i = node.childNodes.length - 1; i >= 0; i--) {{
      if (node.childNodes[i].nodeType !== 1 || !/^(script|style|iframe)$/i.test(node.childNodes[i].tagName)) {{
        walkText(node.childNodes[i], q);
      }}
    }}
  }}
}}

document.getElementById('search').addEventListener('input', filter);
filter();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("Fetching RSS feed (starting at page 0)...")
    eps = fetch_rss()
    print(f"  {len(eps)} total episodes")

    print("Generating listing...")
    html_out = generate_html(eps)
    with open("listing.html", "w") as f:
        f.write(html_out)

    print(f"Done. {len(eps)} episodes ({len(html_out)} bytes)")
