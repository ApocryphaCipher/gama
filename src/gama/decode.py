"""Decode a RAM dump into rows, one list of dicts per table.

Only fields checked against the running game are decoded; the few that
are still guesses say so in a comment and in the README. Offsets are
record-relative and match the save file (see Mirror's
docs/reference/live-ram-map.md and wizard-record-and-exploration.md).
"""

import json

from gama.layout import (
    CITIES,
    DGROUP,
    ENCOUNTERS,
    NODES,
    UNIT_COUNT,
    UNIT_TYPES,
    UNITS,
    WIZARDS,
    u16,
)


def _cstr(data: bytes) -> str:
    return data.split(b"\0")[0].decode("latin-1")


def _i8(value: int) -> int:
    return value - 256 if value >= 128 else value


def _i16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little", signed=True)


def unit_type_name(dump: bytes, unit_type: int) -> str:
    pointer = u16(UNIT_TYPES.record(dump, unit_type), 0)
    return _cstr(dump[DGROUP + pointer : DGROUP + pointer + 32])


def wizards(dump: bytes) -> list[dict]:
    rows = []
    for idx in range(WIZARDS.count):
        r = WIZARDS.record(dump, idx)
        rows.append(
            {
                "idx": idx,
                "name": _cstr(r[0x01:0x15]),
                "banner": r[0x16],
                "fame": u16(r, 0x24),
                "power_base": u16(r, 0x26),
                # Research and mana share order is kazzmir's; only the
                # skill share has been checked against the Magic screen.
                "research_share": r[0x2A],
                "mana_share": r[0x2B],
                "skill_share": r[0x2C],
                "skill_left": u16(r, 0x54),
                "nominal_skill": u16(r, 0x56),
                "research_left": u16(r, 0x25A),
                "mana": u16(r, 0x25C),
                # Guess: casting skill points (only ever rises).
                "casting_skill_points": u16(r, 0x25E),
                "research_spell": u16(r, 0x262),
                "gold": u16(r, 0x356),
            }
        )
    return rows


def cities(dump: bytes) -> list[dict]:
    rows = []
    for idx in range(CITIES.count):
        r = CITIES.record(dump, idx)
        if not r[0]:
            continue
        rows.append(
            {
                "idx": idx,
                "name": _cstr(r[0:14]),
                "race": r[14],
                "x": r[15],
                "y": r[16],
                "plane": r[17],
                "owner": r[18],
                "size": r[19],
                "population": r[20] * 1000 + u16(r, 24) * 10,
                "producing": u16(r, 28),
                "buildings": json.dumps([n for n in range(1, 36) if r[31 + n] == 1]),
                "production_per_turn": r[93],
                "stored_production": u16(r, 94),
                "gold_per_turn": r[96],
                # Guess: the 26 city enchantments; zero in every city seen.
                "enchantment_block": r[67:93].hex(),
            }
        )
    return rows


def units(dump: bytes) -> list[dict]:
    rows = []
    for slot in range(u16(dump, UNIT_COUNT)):
        r = UNITS.record(dump, slot)
        rows.append(
            {
                "slot": slot,
                "x": r[0],
                "y": r[1],
                "plane": r[2],
                "owner": r[3],
                "type": r[5],
                "type_name": unit_type_name(dump, r[5]),
                "dead": int(r[2] == 0xFF),
                "moves_per_turn_halves": r[4],
                "moves_left_halves": r[8],
                "dest_x": r[9],
                "dest_y": r[10],
                # Guess: experience (+1 per turn, 0 on summoned units).
                "experience": r[14],
                "orders": r[18],
                "enchantments": int.from_bytes(r[24:28], "little"),
            }
        )
    return rows


def nodes(dump: bytes) -> list[dict]:
    rows = []
    for idx in range(NODES.count):
        r = NODES.record(dump, idx)
        power = r[4]
        aura = [[r[5 + i], r[25 + i]] for i in range(min(power, 20))]
        rows.append(
            {
                "idx": idx,
                "x": r[0],
                "y": r[1],
                "plane": r[2],
                "owner": _i8(r[3]),
                "power": power,
                "aura": json.dumps(aura),
                "realm": r[45],
            }
        )
    return rows


def encounters(dump: bytes) -> list[dict]:
    rows = []
    for idx in range(ENCOUNTERS.count):
        r = ENCOUNTERS.record(dump, idx)
        rows.append(
            {
                "idx": idx,
                "x": r[0],
                "y": r[1],
                "plane": r[2],
                "intact": r[3],
                "kind": r[4],
                "guard1_type": r[5],
                "guard1_left": r[6] & 0xF,
                "guard1_start": r[6] >> 4,
                "guard2_type": r[7],
                "guard2_left": r[8] & 0xF,
                "guard2_start": r[8] >> 4,
                "gold": _i16(r, 10),
                "mana": _i16(r, 12),
                "spell": r[14],
                # Guess: which wizards have explored the site.
                "explored_flags": r[15],
                "item_count": r[16],
            }
        )
    return rows


TABLES = {
    "wizards": wizards,
    "cities": cities,
    "units": units,
    "nodes": nodes,
    "encounters": encounters,
}
