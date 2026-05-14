# So Videogames Podcast - Workflow

## Primary: Episode listing

```bash
python3 build_listing.py
open listing.html
```

Fetches RSS (paginated from page 0), sanitizes safe HTML tags, writes `listing.html`. Count shows `N / 486 episodes`.

## Experimental: Game extraction

```bash
# Requires Ollama + RAWG API key in .env
python3 build.py
open index.html
```

Extracts game names from descriptions via Ollama, looks up cover art + Metacritic via RAWG. Uses `cache.json` for incremental builds.

**Status**: WIP — 46 episodes have 0 games, 144 entries are merged (two games treated as one).

## Dependencies

- Python stdlib (`urllib`, `xml`, `json`, `re`)
- Ollama (optional): `llama3.2:latest`
- RAWG key (optional): free tier, 20k req/month

## Notes

- RSS returns 366 / 486 episodes (pre-2019 not in feed)
- `listing.html` preserves HTML formatting
- `index.html` strips all HTML (plain text descriptions)
