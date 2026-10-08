# What `gama checkpoint` does

The one call to make at every moment worth keeping. Source: `Store.checkpoint()`
in [`store.py`](../../src/gama/store.py).

```bash
export EVI_HOME=~/repo/mom-evi-vault
uv run gama checkpoint "bought granary" --note "Hamburg city screen"
```

## Steps

1. Take the time (UTC, seconds) and build a **name**:
   `<yyyymmddThhmmss>-<label as a lower-case slug>`, e.g.
   `20260924T151322-bought-granary`.
2. Ask the running DOSBox for **all 16 MB of memory** and file it in the vault as
   `<name>.bin`, a RAM dump (stored as shared 4 KB pages; see Evi's
   [vault-layout.md](https://github.com/ApocryphaCipher/evi/blob/main/docs/reference/vault-layout.md)).
3. Ask for the **CPU registers** and file them as `<name>.cpu.json`, a child of the
   dump.
4. Ask for a **raw screenshot** and file it as `<name>.png`, also a child of the
   dump. If the DOSBox build has no screenshot endpoint, print
   `gama: no screenshot (...)` and go on.
5. **Decode** the dump into the derived tables
   ([derived-tables.md](derived-tables.md)) and record the checkpoint.

The collection defaults to `mom-live-<today>`; override with `--collection`.

## What gets recorded as provenance

| Item | `source` | `license` |
| --- | --- | --- |
| the dump | `DOSBox fork API at <url>` | `game data: never publish raw dumps; short excerpts are fine` |
| registers, screenshot | the same | `our capture of the game: fine to use in reports` |

The item `path` records the exact request and time, e.g.
`http://127.0.0.1:8086/api/v1/memory/0/16777216 @ 2026-09-24T15:13:22+00:00`.

## Adding dumps you already have

`gama ingest DIR --collection NAME --source "..." --license "..."` adds
`*.bin` files (oldest first) to the vault and decodes them. `gama index` decodes
dumps already in the vault that gama hasn't seen, and `gama rebuild` decodes
everything again after a decoder changes.

## Pausing for the moment

If a signature has `"actions": ["pause"]`, the game stops at the hit. Take the
checkpoint while it is paused (the fork's API still answers then), then
`POST /api/v1/dosbox/resume`.
