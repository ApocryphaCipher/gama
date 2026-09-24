# gama: game analytics

Turns RAM dumps of Master of Magic, running in the DOSBox Staging fork
(`~/repo/c++/dosbox-staging`, branch `webserver-write-guard`), into a
SQLite dataset you can query.

Rules it keeps:

- **Raw evidence is never replaced.** Every dump is stored once,
  zstd-compressed, named by its SHA-256. The decoded tables are derived:
  `gama rebuild` re-decodes every stored dump when a decoder improves.
- **Only checked fields are decoded.** A column is either checked against
  the running game or marked as a guess below.
- **No game files in git.** The data lives in `GAMA_HOME`
  (default `~/.mirror/dev/DOSbox/gama`), not in this repo.

## Use

```bash
uv run gama ingest ~/.mirror/dev/DOSbox/ram-dumps-2026-09-23      # a folder of *.bin, or files
uv run gama ingest dump.bin --name "turn 5 map" --note "after buying a granary"
uv run gama sql "SELECT c.name, ci.population FROM cities ci JOIN checkpoints c ON c.id = ci.checkpoint_id WHERE ci.name = 'Hamburg'"
uv run gama rebuild
```

The database is `$GAMA_HOME/gama.sqlite`; any SQLite tool (or DuckDB)
can open it.

## Tables

One row per record per checkpoint, joined to `checkpoints` by
`checkpoint_id`.

| Table | Rows | Notes |
| --- | --- | --- |
| `checkpoints` | one per stored dump | name, time, dump hash, optional screenshot and note; `layout_error` says why a dump wasn't decoded |
| `wizards` | 5 | gold, mana, fame, power base, skill, research |
| `cities` | cities with a name | population, size, race, owner, production, `buildings` (JSON list of building ids) |
| `units` | slots below the unit count | `dead` = 1 for killed units (the game marks them in place with plane `0xff`) |
| `nodes` | 30 | owner (−1 = nobody), power, `aura` (JSON list of tiles), realm (0 Sorcery, 1 Nature, 2 Chaos) |
| `encounters` | 102 | lairs, temples, keeps, node guardians: kind, intact, guards left/at start, rewards |

**Still guesses:** `wizards.casting_skill_points`,
`wizards.research_share` / `mana_share` order, `cities.enchantment_block`,
`units.experience`, `encounters.explored_flags`. Where each field was
checked is recorded in Mirror's `docs/reference/live-ram-map.md`.

## Where the tables are

`src/gama/layout.py` holds the RAM addresses. They held across two DOSBox
launches but aren't guaranteed; a dump that doesn't fit is stored but not
decoded, with the reason in `checkpoints.layout_error`.

## Develop

```bash
uv run pytest
```
