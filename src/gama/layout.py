"""Where Master of Magic keeps its tables in DOSBox RAM.

Addresses were found with the DOSBox fork's memory API and are recorded,
with how each was checked, in Mirror's docs/reference/live-ram-map.md.
They held across two launches with the same DOSBox config, but they are
not guaranteed: `check()` refuses a dump whose tables don't look right
instead of decoding garbage.
"""

from dataclasses import dataclass

DGROUP = 0x289F0  # the game's data segment (SS = 0x289f)


@dataclass(frozen=True)
class Table:
    base: int
    stride: int
    count: int

    def record(self, dump: bytes, index: int) -> bytes:
        start = self.base + index * self.stride
        return dump[start : start + self.stride]


WIZARDS = Table(base=0x328BA, stride=0x4C8, count=5)
CITIES = Table(base=0x6F980, stride=114, count=100)
UNITS = Table(base=0x7E060, stride=32, count=1009)
NODES = Table(base=0x85FE0, stride=48, count=30)
ENCOUNTERS = Table(base=0x86660, stride=24, count=102)
UNIT_TYPES = Table(base=DGROUP + 0x19C, stride=0x24, count=256)

UNIT_COUNT = 0x34782  # u16

# Map planes: 2 planes (0 Arcanus, 1 Myrror) x 40 rows x 60 columns.
MAP_WIDTH, MAP_HEIGHT = 60, 40
MAP_SIZE = MAP_WIDTH * MAP_HEIGHT
TERRAIN = 0x72630  # u16 per tile
MINERALS = 0x760B0  # u8 per tile: specials such as 64 = wild game
EXPLORED = 0x78690  # u8 per tile: 0 = unexplored
TERRAIN_FLAGS = 0x773A0  # u8 per tile: 0x20 = corrupted

# Where save-file (SAVEn.GAM) blocks live in RAM, from the game's own
# writes (Mirror docs/reference/save-to-ram-map.md): (file offset, bytes, RAM).
SAVE_SIZE = 123300
SAVE_BLOCKS = [
    (0x09E8, 7344, WIZARDS.base),
    (0x2698, 9600, TERRAIN),
    (0x8AAC, 11400, CITIES.base),
    (0x13554, 4800, MINERALS),
    (0x14814, 4800, EXPLORED),
    (0x1CBB8, 4800, TERRAIN_FLAGS),
]


def ram_from_save(save: bytes) -> bytes:
    """Place a save file's map, city and wizard blocks where the game keeps
    them in RAM, so the same readers work on saves and dumps."""
    ram = bytearray(max(address + length for _, length, address in SAVE_BLOCKS))
    for offset, length, address in SAVE_BLOCKS:
        ram[address : address + length] = save[offset : offset + length]
    return bytes(ram)


def u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def check(dump: bytes) -> str | None:
    """Return why the dump doesn't match this layout, or None if it does."""
    if len(dump) < ENCOUNTERS.base + ENCOUNTERS.stride * ENCOUNTERS.count:
        return f"dump is only {len(dump)} bytes"

    name = WIZARDS.record(dump, 0)[1:21].split(b"\0")[0]
    if not name or not name.isascii() or not name.decode().isprintable():
        return "wizard 0 has no readable name"

    unit_count = u16(dump, UNIT_COUNT)
    if not 0 < unit_count <= UNITS.count:
        return f"unit count {unit_count} is out of range"

    for i in range(NODES.count):
        x, y, plane = NODES.record(dump, i)[:3]
        if x >= 60 or y >= 40 or plane > 1:
            return f"node {i} is off the map at ({x}, {y}, {plane})"

    return None
