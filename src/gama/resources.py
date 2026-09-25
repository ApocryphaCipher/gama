"""The Surveyor's "City Resources": maximum population, production bonus
and gold bonus for a tile, as the game shows them.

A restatement in our own words of rules read in ReMoM (jbalcomb/ReMoM,
commit a9cc082, MoM/src/CITYCALC.c and Terrain.c; no licence, so nothing
is copied), checked against six Surveyor readouts. Mirror's
docs/reference/surveyor-formula.md explains each rule and its evidence.
"""

from dataclasses import dataclass, field

from gama import layout

WILD_GAME = 64

# Buildings (ids as in the city record's built flags at +31+id).
MARKETPLACE, BANK, MERCHANTS_GUILD = 26, 27, 28
GRANARY, FARMERS_MARKET = 29, 30
SAWMILL, FORESTERS_GUILD, MECHANICIANS_GUILD, MINERS_GUILD = 15, 31, 33, 34
PRODUCTION_BUILDINGS = {SAWMILL: 25, FORESTERS_GUILD: 25, MINERS_GUILD: 50, MECHANICIANS_GUILD: 50}
GOLD_BUILDINGS = {MERCHANTS_GUILD: 100, BANK: 50, MARKETPLACE: 50}

# City enchantment slots (the 26 bytes at +0x43).
FAMINE, GAIAS_BLESSING, INSPIRATIONS, PROSPERITY = 0x07, 0x11, 0x12, 0x13
CORRUPTED = 0x20  # terrain flag
NOMAD = 11

# Single tiles 0xA2..0xB8: (half-food, production %).
_BASE_TILES = {
    **dict.fromkeys((0xA2, 0xAC, 0xAD, 0xB4), (3, 0)),  # grassland
    **dict.fromkeys((0xA3, 0xB7, 0xB8), (1, 3)),  # forest
    0xA4: (0, 5),  # mountain
    0xA5: (0, 0),  # desert (first variant gives no production)
    **dict.fromkeys((0xAE, 0xAF, 0xB0), (0, 3)),  # desert
    0xA8: (4, 0),  # sorcery node
    0xA9: (5, 3),  # nature node
    0xAA: (0, 5),  # chaos node
    0xAB: (1, 3),  # hills
    # swamp, tundra and volcano give nothing
}

# Families of joined tiles, by index range (inclusive): (half-food, production %).
_RANGES = [
    (0xB9, 0x102, (4, 0)),  # rivers, lakes, inland shores
    (0x103, 0x112, (0, 5)),  # mountain ranges
    (0x113, 0x123, (1, 3)),  # hill ranges
    (0x124, 0x1C3, (0, 3)),  # desert ranges
    (0x1C4, 0x1D3, (1, 0)),  # shores
    (0x1D4, 0x1D8, (4, 0)),  # four-way rivers
    (0x1D9, 0x258, (1, 0)),  # shores
]


def tile_kind(value: int) -> int:
    """Terrain values above 761 are animation frames of the same tile."""
    return value % 762


def tile_food_and_production(value: int) -> tuple[int, int]:
    """Food in halves (grassland 3 = 1½ food) and production bonus in %."""
    t = tile_kind(value)
    if t == 0 or t >= 0x259:
        return 0, 0  # ocean, and tundra
    if t == 1:
        return 3, 0
    if t < 0xA2:
        return 1, 0  # shore
    if t in _BASE_TILES:
        return _BASE_TILES[t]
    for first, last, values in _RANGES:
        if first <= t <= last:
            return values
    return 0, 0


def is_river(value: int) -> bool:
    t = tile_kind(value)
    return 0xB9 <= t <= 0xC4 or 0xE9 <= t <= 0x102 or 0x1D4 <= t <= 0x1D8


def is_water(value: int) -> bool:
    """Ocean, shore and lake: what makes a neighbouring city coastal."""
    t = tile_kind(value)
    return (t <= 0xA1 and t != 1) or 0xC5 <= t <= 0xE8 or 0x1C4 <= t <= 0x1D3 or 0x1D9 <= t <= 0x25A


def catchment(x: int, y: int) -> list[tuple[int, int]]:
    """The 21 tiles a city works: 5 x 5 without the corners; x wraps, y doesn't."""
    return [
        ((x + dx) % layout.MAP_WIDTH, y + dy)
        for dy in range(-2, 3)
        for dx in range(-2, 3)
        if not (abs(dx) == 2 and abs(dy) == 2) and 0 <= y + dy < layout.MAP_HEIGHT
    ]


@dataclass
class CityResources:
    max_pop: int
    production: int  # %
    gold: int  # %
    notes: dict = field(default_factory=dict)


class Map:
    def __init__(self, dump: bytes):
        self.dump = dump

    def _index(self, x: int, y: int, plane: int) -> int:
        return plane * layout.MAP_SIZE + y * layout.MAP_WIDTH + x

    def terrain(self, x: int, y: int, plane: int) -> int:
        return layout.u16(self.dump, layout.TERRAIN + 2 * self._index(x, y, plane))

    def mineral(self, x: int, y: int, plane: int) -> int:
        return self.dump[layout.MINERALS + self._index(x, y, plane)]

    def explored(self, x: int, y: int, plane: int) -> bool:
        return self.dump[layout.EXPLORED + self._index(x, y, plane)] != 0

    def corrupted(self, x: int, y: int, plane: int) -> bool:
        return self.dump[layout.TERRAIN_FLAGS + self._index(x, y, plane)] & CORRUPTED != 0

    def cities(self):
        for i in range(layout.CITIES.count):
            record = layout.CITIES.record(self.dump, i)
            if record[0] and record[17] <= 1:
                yield i, record


def _built(city: bytes, building: int) -> bool:
    return city[31 + building] in (0, 1)  # 1 built, 0 replaced by a better one


def city_max_pop(world: Map, city: bytes, shared: set) -> int:
    """A city's maximum population: its uncorrupted tiles' food (explored or
    not; a tile another city also works gives half, rounded only after
    summing), x1.5 with Gaia's Blessing, halved by Famine, plus buildings
    and wild game (2 food, 1 on a shared tile)."""
    x, y, plane = city[15:18]
    tiles = [t for t in catchment(x, y) if not world.corrupted(*t, plane)]
    half_food = sum(
        tile_food_and_production(world.terrain(*t, plane))[0] / (2 if t in shared else 1) for t in tiles
    )
    enchantments = city[0x43 : 0x43 + 26]
    if enchantments[GAIAS_BLESSING]:
        half_food = half_food * 3 / 2
    max_pop = int(half_food) // 2
    if enchantments[FAMINE]:
        max_pop //= 2
    max_pop += 2 * _built(city, GRANARY) + 3 * _built(city, FARMERS_MARKET)
    max_pop += sum(1 if t in shared else 2 for t in tiles if world.mineral(*t, plane) & WILD_GAME)
    return max_pop


def road_trade_bonus(dump: bytes, index: int) -> int:
    """Each city joined by road adds its population in % (half for the same
    race), up to 3% per thousand of this city's own. Unchecked: no readout
    had roads."""
    city = layout.CITIES.record(dump, index)
    links = city[0x65 : 0x65 + 13]  # one bit per city index
    bonus = 0
    for i in range(layout.CITIES.count):
        other = layout.CITIES.record(dump, i)
        if i != index and links[i // 8] & (1 << (i % 8)):
            bonus += other[0x14] if other[14] != city[14] else other[0x14] // 2
    return min(bonus, 3 * city[0x14])


def city_resources(dump: bytes, x: int, y: int, plane: int) -> CityResources:
    world = Map(dump)
    city = city_index = None
    claimed = set()  # tiles in another city's catchment
    for i, record in world.cities():
        if tuple(record[15:18]) == (x, y, plane):
            city, city_index = record, i
        elif record[17] == plane:
            claimed.update(catchment(record[15], record[16]))

    river = is_river(world.terrain(x, y, plane))
    coast = any(
        is_water(world.terrain((x + dx) % layout.MAP_WIDTH, y + dy, plane))
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dx or dy) and 0 <= y + dy < layout.MAP_HEIGHT
    )
    gold = 10 * coast + 20 * river

    food = production = wild_game = 0.0
    for tx, ty in catchment(x, y):
        if not world.explored(tx, ty, plane):
            continue
        tile_food, tile_production = tile_food_and_production(world.terrain(tx, ty, plane))
        game = 1 if world.mineral(tx, ty, plane) & WILD_GAME else 0
        shared = (tx, ty) in claimed
        # A tile another city also works gives half its production, rounded
        # down per tile, to a city and an empty site alike (checked: Steyr).
        production += tile_production // 2 if shared else tile_production
        # Food: an empty site counts it at half (unchecked); a city in full.
        share = 0.5 if city is None and shared else 1
        food += tile_food * share
        wild_game += game * share

    notes = {"half_food": food, "wild_game": wild_game, "river": river, "coast": coast}
    if city is None:
        # Counted in quarter food, and wild game adds only a quarter food
        # per tile here, not the 2 food a city gets from it.
        max_pop = int(2 * food + wild_game) // 4
    else:
        max_pop = city_max_pop(world, city, claimed)
        production += sum(v for b, v in PRODUCTION_BUILDINGS.items() if _built(city, b))
        enchantments = city[0x43 : 0x43 + 26]
        production += 100 if enchantments[INSPIRATIONS] else 0
        gold += 50 if city[14] == NOMAD else 0
        gold += road_trade_bonus(dump, city_index)
        gold = min(gold, 3 * city[0x14])  # at most 3% per thousand people
        gold += sum(v for b, v in GOLD_BUILDINGS.items() if _built(city, b))
        gold += 100 if enchantments[PROSPERITY] else 0
        notes["population"] = city[0x14]

    return CityResources(min(max_pop, 25), int(production), gold, notes)
