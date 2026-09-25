"""The Surveyor hover log: which tile each logged panel text belongs to,
and whether the text agrees with the tile rules in `resources`.

The DOSBox fork's `surveyor-text` watch snapshots the game's UI text
slots with the mouse position; `map-view` and `map-plane` hits say where
the map was. The slots are reused and overwritten, so a snapshot holds
fragments ("/2 food", "5% production"), and a fragment can still be the
previous tile's. So a check reports agreements and conflicts; it can't
prove a single hover.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from gama import resources

MAP_TILE_W, MAP_TILE_H, MAP_TOP, MAP_COLS, MAP_ROWS = 20, 18, 20, 12, 10


def hovered_tile(mouse, origin):
    """Map tile under the mouse (INT 33h coordinates, x 0..639), or None."""
    if not mouse or not origin:
        return None
    px, py = mouse[0] // 2, mouse[1]
    col, row = px // MAP_TILE_W, (py - MAP_TOP) // MAP_TILE_H
    if py < MAP_TOP or not (0 <= col < MAP_COLS and 0 <= row < MAP_ROWS):
        return None
    return ((origin[0] + col) % 60, origin[1] + row)


@dataclass(frozen=True)
class Hover:
    time: str
    mouse: tuple | None
    tile: tuple | None
    plane: int | None
    texts: list  # strings the game had just written


def hovers(log: Path, origin=None, plane=None):
    """Each surveyor-text hit, with the tile and plane in view at the time."""
    for line in Path(log).read_text().splitlines():
        hit = json.loads(line)
        if hit.get("bulk"):
            continue
        if hit["signature"] == "map-view":
            raw = bytes.fromhex(hit["new"].replace(" ", ""))
            origin = (int.from_bytes(raw[0:2], "little"), int.from_bytes(raw[2:4], "little"))
            if origin == (0xFFFF, 0xFFFF):
                origin = None  # the game clears it while off the map (city screen etc.)
            continue
        if hit["signature"] == "map-plane":
            plane = hit["new_value"]
            continue
        if not hit["signature"].startswith("surveyor-text"):
            continue
        new = bytes.fromhex(hit["new"].replace(" ", ""))
        old = bytes.fromhex(hit["old"].replace(" ", ""))
        # Keep only the strings that changed: the slots the game just wrote.
        texts = [m.group().decode() for m in re.finditer(rb"[ -~]{3,}", new)
                 if new[m.start():m.end()] != old[m.start():m.end()]]
        if texts:
            mouse = tuple(hit["mouse"]) if hit.get("mouse") else None
            yield Hover(hit["t"], mouse, hovered_tile(mouse, origin), plane, texts)


def food_text(half_food: int) -> str | None:
    """The panel's food line, e.g. 3 -> '1   1/2 food' (the game pads with spaces)."""
    whole, half = divmod(half_food, 2)
    if half_food == 0:
        return None
    if not half:
        return f"{whole} food"
    return f"{whole}   1/2 food" if whole else "1/2 food"


def production_text(percent: int) -> str | None:
    return f"+{percent}% production" if percent else None


# The panel says swamp gives 1/2 food, but cities count it as 0 (checked:
# Ebonsway's max pop is 9 only with 0; 1/2 would give 11).
SWAMP = (0xA6, 0xB1, 0xB2)


def check(world: resources.Map, hover: Hover) -> str:
    """'agree', 'conflict' or 'silent' (no food or production fragment)."""
    x, y = hover.tile
    terrain = world.terrain(x, y, hover.plane)
    tile_food, tile_production = resources.tile_food_and_production(terrain)
    if resources.tile_kind(terrain) in SWAMP:
        tile_food = 1
    expected = {"food": food_text(tile_food), "production": production_text(tile_production)}
    verdicts = []
    for text in hover.texts:
        fragment = text.strip()
        if fragment.endswith("% production"):
            kind = "production"
        elif fragment.endswith("food") and "+" not in fragment:  # "+2 food" is wild game
            kind = "food"
        else:
            continue
        verdicts.append(bool(expected[kind]) and expected[kind].endswith(fragment))
    if not verdicts:
        return "silent"
    return "agree" if all(verdicts) else "conflict"
