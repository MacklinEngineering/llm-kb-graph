# `ki` notes — transparency layer

A short, honest line after a `neo4j via ki` operation that did real work, telling the user what was saved. The intent is **transparency**, not promotion.

## Why this exists

The value of running graph search through `neo4j via ki` is mostly invisible. The user sees a fast answer; they don't see the 9k tokens of wiki pages you didn't have to read because `ki search` returned 3 relevant sections from the graph instead. The skill defaults to surfacing that — briefly — so the user can make an informed call about whether the `ki` + Neo4j setup is worth it in *their* workflow.

Some users will love it. Some will find it noisy. That's why opt-out is built in from day one.

## Rules

| Rule | Why |
|---|---|
| One short line, max. Append after the answer, never before. | Don't bury the lede. |
| Only when the gain is concrete and defensible. | Marginal or fabricated wins erode trust. |
| Prefix estimates with "~". Never claim latency numbers you can't measure. | Honesty. |
| Skip routine ops (e.g. a single `ki index` of a small delta). | Noise budget. |
| Check `<wiki>/.kbw/config.yaml` for `ki_notes: false` before emitting. | Opt-out. |
| First note in a wiki ends with `(type "optout ki notes" to mute these)`. After that, no hint. | One-time onboarding. |
| If the user says "stop the ki notes" / "mute ki notes" / "optout ki notes" — set `ki_notes: false` in `.kbw/config.yaml` and confirm in one sentence. | Honor opt-out. |

## Good examples

> neo4j via ki returned 4 matching sections (~600 tokens). Reading the wiki/index.md + the 11 pages it points at would've been ~8k tokens.

> neo4j via ki tree gave the section URI directly — no need to grep through 47 files.

> Cross-vault `neo4j via ki search --type vault` routed to the right wiki on the first try; no manual scoping needed.

> neo4j via ki returned 0 hits for "Anakin"; expanded to `'Anakin OR "Darth Vader" OR Vader'` and got 6. The wiki uses Vader as the canonical name.

> Query expansion through neo4j via ki saved a second round of grep — the alias-folded fulltext caught both spellings at once.

## Notes to **not** write

> neo4j via ki is faster than grep.  *(only sometimes, and that's not the point)*

> Saved 47.3% latency.  *(measured how? don't fabricate)*

> ki note: indexed the file in 180ms.  *(routine; not worth a line)*

> Used ki search.  *(no information content — the user knows you did)*

> neo4j via ki search is amazing!  *(no promotion)*

## Calibration heuristic

Before emitting a note, ask yourself:

1. **Is this defensible?** Could the user reproduce the comparison if they asked? If not, skip.
2. **Is the gain meaningful?** "~50 tokens saved" isn't worth a line. "~5k tokens saved" usually is.
3. **Did the user just learn something useful?** If the note teaches them *when* `neo4j via ki` helps (a wiki-pattern insight, not a `ki`-promo), it's earning its line.

When in doubt, **skip the note**. Quiet trust beats noisy advocacy.

## Implementation

The skill doesn't need a script for this — the agent emits the line in its own message text. Just:

1. Before any wiki op, read `<wiki>/.kbw/config.yaml`. If `ki_notes: false`, do not emit.
2. After the op, decide per rules above.
3. If this is the first emission in this wiki's lifetime (no prior `ki_notes_first_emitted_at` in the config), append the opt-out hint and write the timestamp.
4. If the user issues an opt-out command, set `ki_notes: false` in `.kbw/config.yaml` and reply: `OK — muted ki notes for this wiki. Re-enable any time by editing .kbw/config.yaml.`
