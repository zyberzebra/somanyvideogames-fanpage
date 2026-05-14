# So Videogames Podcast - Episode Listing

Search UI for the So Videogames podcast archive. Opens by double-clicking `listing.html` - no server needed.

```bash
python3 build_listing.py
open listing.html
```

## Files

| File | Purpose |
|---|---|
| `listing.html` | Episode listing with search + HTML descriptions (open this) |
| `build_listing.py` | Fetches RSS feed and generates `listing.html` |
| `build.py` | Experimental: game name extraction via Ollama + RAWG cover art |
| `cache.json` | Game extraction cache (WIP, gitignored) |
| `.env` | RAWG API key (optional, for build.py only) |

## Rebuild

```bash
# Main workflow (no deps)
python3 build_listing.py

# Game extraction (WIP - requires Ollama + RAWG key)
python3 build.py
```

## Notes

- **366 / 486** episodes in feed (pre-2019 episodes not available via RSS)
- HTML descriptions preserved in `listing.html`
- Game extraction via `build.py` is work in progress — 46 episodes with 0 games, 144 merged entries
