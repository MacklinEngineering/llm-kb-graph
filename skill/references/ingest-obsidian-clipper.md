# Ingest pattern: Obsidian Web Clipper → `raw/articles/`

Karpathy's preferred path for getting web articles into the wiki. The Web Clipper is a browser extension that converts the page you're on into a clean `.md` file (with images downloaded locally if you want).

## Why this is good

- Two clicks per article. No copy-paste.
- Clean markdown — strips ads, sidebars, footers.
- Optionally downloads images, so the wiki stays portable when offline.
- Writes the file directly into a folder; the agent picks it up on the next `ingest`.

## Install

1. Install the Obsidian Web Clipper extension: <https://obsidian.md/clipper> (works in Chrome, Firefox, Safari, Edge).
2. Open the extension → **Settings**.
3. Set the **Vault** to the wiki root (e.g. `~/Documents/ai-wiki`).
4. Set the **Folder** to `raw/articles`.
5. (Optional) Toggle **Download images locally** if you want offline portability.
6. (Recommended) Set the **filename template** to `{{date:YYYY-MM-DD}}-{{title}}` so the agent gets a clean slug.

## Hotkey for images

Karpathy's tip: bind a browser hotkey for "download all related images" so any image referenced in the clipped article ends up on disk too. The extension's settings let you pick a hotkey for "Download images."

## After clipping

The agent should treat newly-clipped files in `raw/articles/` like any other new source — run `ingest` (which will write a summary, update concepts/entities, etc., then `ki index`).

A handy one-liner to see what's new since the last ingest:

```bash
find <wiki-root>/raw/articles -name '*.md' -newer <wiki-root>/wiki/summaries -type f
```

Then for each file: read, summarize, integrate, index, log.

## Config

`<wiki>/.kbw/config.yaml`:

```yaml
ingest:
  obsidian_clipper:
    enabled: true
    folder: raw/articles   # where the Clipper writes
```

## Alternatives if not using a browser

- **Reader Mode → Save As → `raw/articles/`**: every modern browser has a reader-mode view. "Save as Webpage, Complete" → run `markitdown` on the `.html`.
- **Manual paste**: paste the article body into a `.txt` in `raw/inbox/`. Less clean, but works.
