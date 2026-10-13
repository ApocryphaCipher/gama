# Derived tables

The database is `$EVI_HOME/derived/gama.sqlite`. **Everything in it is
derived** from the dumps in the Evi vault: `gama rebuild` drops and recreates
the decoded tables, and a change to `SCHEMA_VERSION` (now 2) in
[`store.py`](../../src/gama/store.py) rebuilds the whole database the next time
it is opened.

Source: [`decode.py`](../../src/gama/decode.py) for the columns,
[`store.py`](../../src/gama/store.py) for how they are stored. Only fields
**checked against the running game** are decoded, apart from the ones marked
*guess* below. Where each field was checked is in Mirror's
`docs/reference/live-ram-map.md`.

Every decoded table has a `checkpoint_id` column, joined to
`checkpoints.id`. One row per record per checkpoint.

## `checkpoints`

One row per dump.

| Column | Meaning |
| --- | --- |
| `id` | the checkpoint |
| `evi_item_id` | the dump's item in the Evi catalogue (unique) |
| `dump_sha256` | the dump's hash |
| `name` | the item name without `.bin`; for `gama checkpoint` it is `<timestamp>-<label slug>` |
| `collection` | the Evi collection |
| `taken_at` | the dump's file time |
| `note` | what was on screen |
| `screenshot_evi_item_id` | a screenshot taken with the dump, if any (the first child image) |
| `layout_error` | why the dump wasn't decoded, or `NULL`. See [ram-layout.md](ram-layout.md) |

## `wizards`: 5 rows per decoded dump

`idx`, `name`, `banner`, `fame`, `power_base`, `research_share`, `mana_share`,
`skill_share`, `skill_left`, `nominal_skill`, `research_left`, `mana`,
`casting_skill_points`, `research_spell`, `gold`.

*Guesses:* `casting_skill_points` (only ever rises), and the **order** of
`research_share` and `mana_share` (the order is kazzmir's; only the skill share
was checked against the Magic screen).

## `cities`: only records with a name

`idx`, `name`, `race`, `x`, `y`, `plane`, `owner`, `size`, `population`,
`producing`, `buildings`, `production_per_turn`, `stored_production`,
`gold_per_turn`, `enchantment_block`.

- `population` is the byte at record offset 20 times 1,000, plus the `u16` at
  offset 24 times 10.
- `buildings` is a **JSON list** of building ids (1 to 35) whose flag is 1.
- *Guess:* `enchantment_block`, the 26 city-enchantment bytes as hex. It was
  zero in every city seen. (gama's `resources` module reads the same bytes by
  slot, for Famine, Gaia's Blessing, Inspirations and Prosperity.)

## `units`: slots below the unit count

`slot`, `x`, `y`, `plane`, `owner`, `type`, `type_name`, `dead`,
`moves_per_turn_halves`, `moves_left_halves`, `dest_x`, `dest_y`,
`experience`, `orders`, `enchantments`.

- `dead` is 1 when the game has marked the unit in place with plane `0xFF`.
- `type_name` is read from the game's own unit-type name table.
- `*_halves` are in half-moves.
- *Guess:* `experience` (+1 per turn, 0 on summoned units).

## `nodes`: 30 rows

`idx`, `x`, `y`, `plane`, `owner` (−1 = nobody), `power`, `aura`, `realm`.

- `aura` is a **JSON list** of `[x, y]` tiles, at most 20.
- `realm`: 0 Sorcery, 1 Nature, 2 Chaos.

## `encounters`: 102 rows

Lairs, temples, keeps and node guardians. `idx`, `x`, `y`, `plane`, `intact`,
`kind`, `guard1_type`, `guard1_left`, `guard1_start`, `guard2_type`,
`guard2_left`, `guard2_start`, `gold`, `mana`, `spell`, `explored_flags`,
`item_count`.

- `*_left` and `*_start` are the low and high nibbles of one byte: guards left
  now, and at the start.
- *Guess:* `explored_flags` (which wizards have explored the site).

## Behaviour to know

- A decoded table is created from the first dump that has rows for it. If no
  dump ever has a row (say, no city has a name) the table doesn't exist, and
  `gama sql` on it fails with "no such table".
- A dump that fails the layout check gets a `checkpoints` row with
  `layout_error` set and **no** rows in the decoded tables.
- Example: a city's population over time.

```bash
uv run gama sql "SELECT c.name, ci.population FROM cities ci JOIN checkpoints c ON c.id = ci.checkpoint_id WHERE ci.name = 'Hamburg' ORDER BY c.taken_at"
```
