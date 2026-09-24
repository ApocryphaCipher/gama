# gama: game analytics

Part of **ApocryphaCipher**: delving into the apocryphal to reconstruct
long-lost, undocumented code (inspired by the Apocrypha, the realm of
lost and forbidden knowledge in The Elder Scrolls Online). Its tools
support forensic investigation of software, namely 90s DOS games. The
other tools so far are a DOSBox Staging fork that exposes the running
machine (memory, screenshots) and Mirror, a Master of Magic save viewer.

Turns RAM dumps of Master of Magic, running in the DOSBox Staging fork
(`ApocryphaCipher/dosbox-staging`, branch `webserver-write-guard`), into
SQLite tables you can query. It is the decoding and data layer between
the fork, which captures the running machine, and
[Evi](https://github.com/ApocryphaCipher/evi), which keeps the evidence.

Rules it keeps:

- **gama stores no evidence.** Dumps go into an Evi vault, where they are
  kept as originals (shared 4 KB pages) with their provenance. gama reads
  them from there.
- **Its tables are derived.** They live in the vault's `derived/` folder
  (not versioned), and `gama rebuild` recreates them from the vault
  whenever a decoder improves.
- **Only checked fields are decoded.** A column is either checked against
  the running game or marked as a guess below.

## Use

```bash
export EVI_HOME=~/repo/mom-evi-vault        # the Evi vault to work in
uv run gama ingest dumps/ --collection mom-live-2026-09-23 \
    --source "DOSBox fork memory API" --license "game data: never publish raw"
uv run gama index                           # decode dumps already in the vault
uv run gama sql "SELECT c.name, ci.population FROM cities ci JOIN checkpoints c ON c.id = ci.checkpoint_id WHERE ci.name = 'Hamburg' ORDER BY c.taken_at"
uv run gama rebuild
```

The database is `$EVI_HOME/derived/gama.sqlite`; any SQLite tool (or
DuckDB) can open it, and `checkpoints.evi_item_id` leads back to each
dump's item in the Evi catalogue.

## Tables

One row per record per checkpoint, joined to `checkpoints` by
`checkpoint_id`.

| Table | Rows | Notes |
| --- | --- | --- |
| `checkpoints` | one per decoded dump | Evi item id, dump hash, name, collection, time; `layout_error` says why a dump wasn't decoded |
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
launches but aren't guaranteed; a dump that doesn't fit is recorded but not
decoded, with the reason in `checkpoints.layout_error`.

## Develop

```bash
uv run pytest
```

## Licence

MIT. The licence covers gama's code only, never game data or dumps.
