# RAM layout

Where Master of Magic keeps its tables in DOSBox's emulated memory. The
addresses are **physical (linear) addresses** into a 16 MB dump, taken from
[`layout.py`](../../src/gama/layout.py). They were found with the DOSBox fork's
memory API; how each was checked is recorded in Mirror's
`docs/reference/live-ram-map.md`.

They held across two DOSBox launches with the same configuration, but they are
**not guaranteed**. `WIZARDS.EXE`'s data segment (`DGROUP`, `0x289F0`) is the
anchor; a different DOSBox memory size, or a different build of the game, can
move things.

## Tables

`Table(base, stride, count)`; record `i` is at `base + i * stride`.

| Table | Base | Stride | Count |
| --- | --- | --- | --- |
| wizards | `0x328BA` | `0x4C8` (1,224) | 5 |
| cities | `0x6F980` | 114 | 100 |
| units | `0x7E060` | 32 | 1,009 |
| nodes | `0x85FE0` | 48 | 30 |
| encounters | `0x86660` | 24 | 102 |
| unit types | `DGROUP + 0x19C` | `0x24` (36) | 256 |

The unit count is a `u16` at `0x34782`.

## The map

Two planes (0 Arcanus, 1 Myrror) of 40 rows by 60 columns (`MAP_SIZE` = 2,400
tiles per plane). The world wraps at x = 60.

| Layer | Address | Per tile |
| --- | --- | --- |
| terrain | `0x72630` | `u16` |
| minerals (specials) | `0x760B0` | `u8`; e.g. 64 = wild game |
| explored | `0x78690` | `u8`; 0 = unexplored |
| terrain flags | `0x773A0` | `u8`; `0x20` = corrupted |

## Save file blocks

A `SAVEn.GAM` is 123,300 bytes (`SAVE_SIZE`). `ram_from_save()` copies these
blocks to where the game keeps them in RAM, so the same readers work on a save
and a dump. The offsets come from the game's own writes (Mirror's
`docs/reference/save-to-ram-map.md`; gama's `filemap` command finds them).

| Save offset | Bytes | RAM address |
| --- | --- | --- |
| `0x09E8` | 7,344 | wizards |
| `0x2698` | 9,600 | terrain |
| `0x8AAC` | 11,400 | cities |
| `0x13554` | 4,800 | minerals |
| `0x14814` | 4,800 | explored |
| `0x1CBB8` | 4,800 | terrain flags |

Only these blocks are placed; units, nodes and encounters are not, so a save
file cannot be run through the full decoder.

## The layout check

`check(dump)` refuses a dump that doesn't look like this layout, rather than
decode garbage. A dump fails if:

- it is shorter than the end of the encounters table;
- wizard 0 has no readable name (non-empty, ASCII, printable);
- the unit count is 0 or more than 1,009;
- any node is off the map (x ≥ 60, y ≥ 40, or plane > 1).

The reason becomes `checkpoints.layout_error`.

> *Guess:* the check cannot tell a dump of a different game that happens to pass
> these four tests, but that is unlikely. It has only been used on Master of
> Magic dumps.
