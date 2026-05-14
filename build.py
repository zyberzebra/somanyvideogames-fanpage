import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
import html, re, json, ssl, time, os, hashlib, sys
from http.client import HTTPConnection

RSS_URL = "https://gamecritics.com/category/podcasts/so-videogames/feed/"
NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
ctx = ssl._create_unverified_context()
months = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
          "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"
RAWG_BASE = "https://api.rawg.io/api/games"
CACHE_FILE = "cache.json"

RAWG_KEY = ""
if os.path.exists(".env"):
    for line in open(".env"):
        if line.startswith("RAWG_API_KEY="):
            RAWG_KEY = line.strip().split("=", 1)[1]

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"episodes": {}, "game_index": {}}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

NOISE_WORDS = {"and more", "...and more", "…and more", "and more!", "...and more!", "also", "battle", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "free games", "clicker"}

def extract_games_section(desc):
    patterns = [
        r"(?:covers?|include[s]?|topics? covered?|titles? covered?|games? covered?)\s*:?\s*(.*?)(?:\…\s*and more!|\.\.\.and more!|\.\.and more!|…and more!|\.\.\.and more|and more!|you can also hear|please send feedback)",
        r"(?:covers?|include[s]?|topics? covered?|titles? covered?|games? covered?)\s*:?\s*(.*)",
    ]
    for p in patterns:
        m = re.search(p, desc, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return desc

def clean_games(games):
    cleaned = []
    for g in games:
        g = re.sub(r"\s*\(.*?\)", "", g).strip()
        g = re.sub(r"\s*–.*", "", g).strip()
        g = re.sub(r"\s*…?\s*and more!?\s*", "", g, flags=re.IGNORECASE).strip()
        g = re.sub(r"\s*…$", "", g).strip()
        if not g or len(g) < 2: continue
        if "//" in g or "http" in g: continue
        if g.lower() in NOISE_WORDS: continue
        if re.match(r"^\d{4}$", g): continue
        cleaned.append(g)
    return cleaned

def ollama_extract(descriptions):
    batch = []
    for url, desc in descriptions:
        section = extract_games_section(desc)[:1500]
        batch.append(f"[episode: {url}] {section}")

    prompt = (
        "Extract all video game titles from these podcast episode descriptions. "
        "The games are listed one after another after phrases like 'covers:' or 'include:' "
        "and before '...and more!' or '…And more!'.\n\n"
        "Rules:\n"
        "- Extract each game as a separate title\n"
        "- Include indie, retro, obscure, and unfinished titles\n"
        "- Remove parenthetical notes like (review), (demo), (DLC) from titles\n"
        "- Exclude: platforms, genres, websites, email addresses, episode numbers, generic terms\n"
        "- If a title contains a colon or dash, keep the full title (e.g. 'Max Payne 1 & 3' not 'Max Payne')\n\n"
        "Examples:\n"
        "Input: \"covers: Elden Ring Hades Stray ...and more!\"\n"
        "Output: [\"Elden Ring\", \"Hades\", \"Stray\"]\n\n"
        "Input: \"covers: Crimson Desert (review) Pragmata Lucky Tower ..and more!\"\n"
        "Output: [\"Crimson Desert\", \"Pragmata\", \"Lucky Tower\"]\n\n"
        "Input: \"covers: Sumerian Six Trash Goblin Thomas & Friends: Wonders of Sodor Devil Jam …And more!\"\n"
        "Output: [\"Sumerian Six\", \"Trash Goblin\", \"Thomas & Friends: Wonders of Sodor\", \"Devil Jam\"]\n\n"
        "Input: \"covers: Let Them Come: Onslaught (review) Let Them Come Absolum The Occultist Lucky Tower Pragmata ..and more!\"\n"
        "Output: [\"Let Them Come: Onslaught\", \"Let Them Come\", \"Absolum\", \"The Occultist\", \"Lucky Tower\", \"Pragmata\"]\n\n"
        "Return a JSON object where keys are episode URLs and values are arrays of game title strings.\n\n"
        + "\n---\n".join(batch)
    )

    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            text = result.get("response", "{}")
            return json.loads(text)
    except Exception as e:
        print(f"  Ollama error: {e}")
        return {}

def fetch_rss():
    episodes = []
    page = 1
    while True:
        try:
            with urllib.request.urlopen(f"{RSS_URL}?paged={page}", context=ctx) as resp:
                root = ET.fromstring(resp.read())
        except Exception as e:
            break
        items = root.findall(".//item")
        if not items:
            break
        for item in items:
            url = item.findtext("link", "")
            content_el = item.find("content:encoded", NS)
            desc_html = content_el.text if content_el is not None else item.findtext("description", "")
            for tag in ['<br>', '<br/>', '<br />', '<li>', '</li>', '<p>', '</p>', '</ul>', '<ul>', '<ol>', '</ol>']:
                desc_html = desc_html.replace(tag, '\n')
            desc_text = re.sub(r"<[^>]+>", "", html.unescape(desc_html))
            desc_text = re.sub(r"[ \t]+\n", "\n", desc_text)
            desc_text = re.sub(r"\n[ \t]+", "\n", desc_text)
            desc_text = re.sub(r"\n{3,}", "\n\n", desc_text)
            desc_text = desc_text.strip()
            pub_date = item.findtext("pubDate", "")
            date = ""
            if pub_date:
                parts = pub_date.split()
                if len(parts) >= 4:
                    date = f"{parts[3]}-{months.get(parts[2],'00')}-{parts[1].zfill(2)}"
            episodes.append({
                "title": item.findtext("title", ""),
                "description": desc_text,
                "date": date,
                "url": url,
            })
        print(f"  RSS page {page}: {len(items)} items")
        page += 1
        time.sleep(0.3)
    return episodes

def lookup_rawg(game_name):
    url = f"{RAWG_BASE}?search={urllib.parse.quote(game_name)}&key={RAWG_KEY}&page_size=1"
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                return {
                    "cover": r.get("background_image", ""),
                    "metacritic": r.get("metacritic"),
                    "genres": [g["name"] for g in r.get("genres", [])[:3]],
                    "released": (r.get("released") or "")[:4],
                    "slug": r.get("slug", ""),
                }
    except Exception as e:
        print(f"  RAWG error for '{game_name}': {e}")
    return None

def generate_html(cache):
    ep_list = list(cache["episodes"].values())
    ep_list.sort(key=lambda e: e.get("date", ""), reverse=True)
    game_index = cache.get("game_index", {})

    for ep in ep_list:
        games = ep.get("games", [])
        ep["game_cards"] = []
        for g in games:
            info = game_index.get(g)
            if info and info.get("rawg") and info["rawg"].get("cover"):
                ep["game_cards"].append({"name": g, "rawg": info["rawg"]})

    data_json = json.dumps(ep_list)
    gi_json = json.dumps(game_index)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>So Videogames Podcast – Game Search</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 1rem; }}
#search {{ width: 100%; padding: 0.75rem; font-size: 1.2rem; margin-bottom: 1.5rem; box-sizing: border-box; }}
.ep {{ margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #ddd; }}
.ep-title {{ font-size: 1.1rem; font-weight: bold; }}
.ep-title a {{ color: #1a0dab; text-decoration: none; }}
.ep-title a:hover {{ text-decoration: underline; }}
.ep-date {{ color: #666; font-size: 0.85rem; margin: 0.15rem 0 0.5rem 0; }}
.game-row {{ display: flex; gap: 0.6rem; overflow-x: auto; padding: 0.5rem 0; }}
.game-card {{ flex: 0 0 auto; width: 120px; background: #f5f5f5; border-radius: 6px; overflow: hidden; font-size: 0.75rem; }}
.game-card img {{ width: 120px; height: 64px; object-fit: cover; display: block; background: #ddd; }}
.game-card-body {{ padding: 4px 6px 6px; }}
.game-card-name {{ font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.game-card-meta {{ color: #555; }}
.game-card-meta .score {{ font-weight: 600; }}
.game-card-meta .score.high {{ color: #3a7; }}
.game-card-meta .score.mid {{ color: #a80; }}
.game-card-meta .score.low {{ color: #c33; }}
.desc-toggle {{ color: #666; cursor: pointer; font-size: 0.85rem; user-select: none; }}
.desc-toggle:hover {{ text-decoration: underline; }}
.desc-body {{ margin-top: 0.4rem; font-size: 0.9rem; line-height: 1.4; display: none; }}
.no-matches {{ color: #888; }}
.highlight {{ background: #ffe066; }}
.footer {{ margin-top: 2rem; font-size: 0.8rem; color: #999; text-align: center; }}
</style>
</head>
<body>
<h1>Game Search – So Videogames Podcast</h1>
<input type="text" id="search" placeholder="Type a game name or episode..." autofocus>
<div id="results"></div>
<div class="footer">Data from <a href="https://rawg.io">RAWG</a> · {len(ep_list)} episodes · {len(game_index)} games indexed</div>
<script>
const episodes = {data_json};
const gameIndex = {gi_json};

function filter() {{
  const q = document.getElementById('search').value.toLowerCase().trim();
  const r = document.getElementById('results');
  let filtered = episodes;
  if (q) {{
    filtered = episodes.filter(e => {{
      if (e.title.toLowerCase().includes(q)) return true;
      if (e.description.toLowerCase().includes(q)) return true;
      if ((e.games || []).some(g => g.toLowerCase().includes(q))) return true;
      return false;
    }});
  }}
  r.innerHTML = filtered.length ? filtered.map(e => epHTML(e, q)).join('') : '<p class="no-matches">No matches found.</p>';
}}

function epHTML(e, q) {{
  const title = hl(e.title, q);
  const cards = (e.game_cards || []).map(g => {{
    const info = g.rawg;
    const score = info.metacritic;
    const scClass = score >= 75 ? 'high' : score >= 50 ? 'mid' : 'low';
    const scoreHtml = score != null ? '<span class="score ' + scClass + '">' + score + '</span>' : '—';
    const img = info.cover ? '<img src="' + info.cover + '" alt="" loading="lazy">' : '<div style="height:64px;background:#ddd;display:flex;align-items:center;justify-content:center;color:#999">no img</div>';
    return '<div class="game-card">' + img + '<div class="game-card-body"><div class="game-card-name">' + hl(g.name, q) + '</div><div class="game-card-meta">' + scoreHtml + '</div></div></div>';
  }}).join('');
  const cardsHtml = cards ? '<div class="game-row">' + cards + '</div>' : '';
  const descId = 'd' + e.url.replace(/[^a-zA-Z0-9]/g, '');
  return '<div class="ep"><div class="ep-title"><a href="' + e.url + '" target="_blank">' + title + '</a></div><div class="ep-date">' + e.date + '</div>' + cardsHtml + '<div class="desc-toggle" onclick="document.getElementById(\\'' + descId + '\\').style.display=document.getElementById(\\'' + descId + '\\').style.display==\\'block\\'?\\'none\\':\\'block\\'">▸ Show description</div><div id="' + descId + '" class="desc-body">' + hl(e.description, q) + '</div></div>';
}}

function hl(t, q) {{
  if (!q) return t;
  const re = new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
  return t.replace(re, '<mark class="highlight">$1</mark>');
}}

document.getElementById('search').addEventListener('input', filter);
filter();
</script>
</body>
</html>"""

if __name__ == "__main__":
    if not RAWG_KEY:
        print("WARNING: No RAWG_API_KEY in .env. Game cover art will be unavailable.")
        print("Get a free key at https://rawg.io/apidocs and add to .env:\n  RAWG_API_KEY=your_key_here\n")

    print("Loading cache...")
    cache = load_cache()
    cached_eps = len(cache["episodes"])
    cached_games = len(cache.get("game_index", {}))
    print(f"  {cached_eps} episodes, {cached_games} games cached")

    print("\nFetching RSS feed...")
    fresh_eps = fetch_rss()
    print(f"  {len(fresh_eps)} episodes in feed")

    re_extract = '--re-extract' in sys.argv

    new_eps = [e for e in fresh_eps if e["url"] not in cache["episodes"]]
    print(f"  {len(new_eps)} new episodes to process")

    need_extraction = list(new_eps)
    if re_extract:
        for e in fresh_eps:
            cached = cache["episodes"].get(e["url"])
            if cached is not None:
                games = cached.get("games")
                if not games or any(len(g.split()) > 5 for g in games):
                    cache["episodes"][e["url"]]["games"] = []
                    cache["episodes"][e["url"]]["description"] = e["description"]
                    e["games"] = []
                    need_extraction.append(e)
        extras = len(need_extraction) - len(new_eps)
        if extras:
            print(f"  {extras} cached episodes queued for re-extraction")

    if need_extraction:
        print("\nExtracting game names with Ollama...")
        for i in range(0, len(need_extraction), 20):
            batch = need_extraction[i:i+20]
            batch_data = [(e["url"], e["description"]) for e in batch]
            print(f"  Batch {i//20 + 1}/{(len(need_extraction)-1)//20 + 1}...")
            result = ollama_extract(batch_data)
            for e in batch:
                games = result.get(e["url"], [])
                if isinstance(games, list):
                    games = [g.strip() for g in games if isinstance(g, str) and g.strip()]
                e["games"] = clean_games(games)
            time.sleep(1.0)

        for e in need_extraction:
            cache["episodes"][e["url"]] = {
                "title": e["title"],
                "description": e["description"],
                "date": e["date"],
                "url": e["url"],
                "games": e.get("games", []),
            }

    all_games = set()
    for ep in cache["episodes"].values():
        for g in ep.get("games", []):
            all_games.add(g)

    game_index = cache.get("game_index", {})
    new_games = [g for g in all_games if g not in game_index]

    if new_games and RAWG_KEY:
        print(f"\nLooking up {len(new_games)} games on RAWG...")
        for idx, g in enumerate(new_games):
            print(f"  [{idx+1}/{len(new_games)}] {g[:40]}...", end=" ", flush=True)
            info = lookup_rawg(g)
            if info:
                game_index[g] = {"rawg": info}
                print("found" if info.get("cover") else "no cover")
            else:
                game_index[g] = {"rawg": None}
                print("not found")
            time.sleep(1.1)
        cache["game_index"] = game_index

    did_work = new_eps or new_games or re_extract
    if did_work:
        print("\nSaving cache...")
        save_cache(cache)

    print("\nGenerating index.html...")
    html_out = generate_html(cache)
    with open("index.html", "w") as f:
        f.write(html_out)

    ep_count = len(cache["episodes"])
    gi_count = len(cache.get("game_index", {}))
    print(f"Done. {ep_count} episodes, {gi_count} games indexed ({len(html_out)} bytes)")
