# Open Work

## Known Issues

- **366 / 486 episodes** — RSS Feed liefert nur Eps ab ~120 (2019), ~120 fehlen
- **46 episodes have 0 games** — Ollama-Extraktion fehlgeschlagen oder Episode enthielt keine Spiele
- **144 merged entries** — Zwei oder mehr Games wurden als ein Eintrag erkannt (z.B. "Drill Core TerraTech Legion")
- **"The Artful Escape" fehlt** in Episode 487 (wird wegen "– Carlos' review" weggeschnitten)
- **build.py** und **build_listing.py** teilen sich keine Codebasis (HTML-Sanitierung doppelt, unterschiedliche RSS-Seiten-Startwerte)
- **Kein .env.example** — Setup-Doku verweist darauf, existiert nicht

## Ideas / Future

- **Steam-Links** in Spiele-Cards integrieren (RAWG liefert keine AppID, aber `store.steampowered.com/search/?term=`)
- **Spiel-Genres & Release-Jahr** in Game-Cards anzeigen (RAWG-Daten sind schon da)
- **Ollama-Modell-Upgrade** auf `llama3.1:8b` um merged entries zu reduzieren
- **Fehlende Episoden** — gamecritics.com direkt scrapen statt RSS für Eps < 120
- **Graceful Error** wenn Ollama nicht läuft (aktuell silent fail)
- **Dunkles Theme** für listing.html
- **Teilen-Button** pro Episode (permalink mit Highlight)
