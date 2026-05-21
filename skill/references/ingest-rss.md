# Ingest pattern: RSS / arXiv puller (cron)

For research wikis that should track new papers and blog posts automatically.

## Status

⚠️ The RSS puller script is **not bundled by default** to keep the skill stdlib-only. The agent creates `scripts/rss_pull.py` at the wiki root (not in the skill dir) the first time the user enables this pattern. The template below is what the agent writes.

## Setup

1. Ask the user for their feed list. Save to `<wiki>/.kbw/feeds.txt`, one URL per line. Examples:

   ```
   # arXiv categories
   http://export.arxiv.org/rss/cs.LG
   http://export.arxiv.org/rss/cs.CL

   # blogs
   https://karpathy.github.io/feed.xml
   https://blog.anthropic.com/feed.xml

   # newsletters with RSS
   https://newsletter.example.com/feed
   ```

2. Write the puller script to `<wiki>/scripts/rss_pull.py` (template below).

3. Make sure the user has `feedparser` available (the only non-stdlib dep):

   ```bash
   uv tool install feedparser   # or: pip install feedparser
   ```

4. (Optional) Cron it:

   ```bash
   # crontab -e — pull feeds at 7am daily
   0 7 * * *  /usr/bin/python3 /path/to/wiki/scripts/rss_pull.py /path/to/wiki >> /path/to/wiki/.kbw/log/cron.log 2>&1
   ```

   ⚠️ Cron only fetches feed items into `raw/feeds/`. It does *not* compile the wiki — that needs the LLM. Next time the user opens a session in the wiki dir, the agent will detect new files and offer to compile them.

## Template

The agent writes this file (verbatim) to `<wiki>/scripts/rss_pull.py` on first setup. Adjust the `MAX_PER_FEED` and `FEED_LIST` defaults as the user wants.

```python
#!/usr/bin/env python3
"""Pull RSS feeds into <wiki>/raw/feeds/<feed-slug>/<date>-<entry-slug>.md.

Idempotent — skips entries already on disk by URL hash.
Requires feedparser. Stdlib otherwise.
"""
from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    import feedparser
except ImportError:
    sys.exit("error: feedparser not installed. Run: uv tool install feedparser")

MAX_PER_FEED = 25


def slugify(s: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9\-_ ]", "", s).strip().lower().replace(" ", "-")
    return s[:max_len].strip("-") or "untitled"


def feed_slug(url: str) -> str:
    host = urlparse(url).netloc or "feed"
    return slugify(host.replace(".", "-"))


def write_entry(entry, out_dir: Path) -> bool:
    url = entry.get("link") or entry.get("id") or ""
    if not url:
        return False
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    date = entry.get("published_parsed") or entry.get("updated_parsed")
    date_str = (
        datetime(*date[:6], tzinfo=timezone.utc).date().isoformat()
        if date else datetime.now(timezone.utc).date().isoformat()
    )
    title = entry.get("title", "untitled")
    name = f"{date_str}-{slugify(title)}-{h}.md"
    target = out_dir / name
    if target.exists():
        return False

    body = entry.get("summary") or entry.get("description") or ""
    front = (
        f"---\nurl: {url}\ntitle: {title!r}\nfetched: "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n---\n\n"
    )
    target.write_text(front + body + "\n", encoding="utf-8")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit("usage: rss_pull.py <wiki-root>")
    wiki = Path(sys.argv[1]).expanduser().resolve()
    feeds_file = wiki / ".kbw" / "feeds.txt"
    feeds_root = wiki / "raw" / "feeds"
    if not feeds_file.is_file():
        sys.exit(f"error: {feeds_file} not found")
    feeds_root.mkdir(parents=True, exist_ok=True)

    urls = [
        line.strip()
        for line in feeds_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    added = 0
    for url in urls:
        out_dir = feeds_root / feed_slug(url)
        out_dir.mkdir(exist_ok=True)
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:MAX_PER_FEED]:
            if write_entry(entry, out_dir):
                added += 1
    print(f"rss_pull: added {added} new entries across {len(urls)} feeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Config

`<wiki>/.kbw/config.yaml`:

```yaml
ingest:
  rss:
    enabled: true
    feeds_file: .kbw/feeds.txt
    output: raw/feeds/
    schedule: "0 7 * * *"   # informational only; cron itself lives outside the wiki
```
