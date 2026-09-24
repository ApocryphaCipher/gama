"""Tests on a synthetic dump built from the proven record layouts."""

import json

from evi.vault import Provenance, Vault

from gama import decode, layout
from gama.store import Store

DUMP_SIZE = 16 * 1024 * 1024


def put(dump: bytearray, address: int, data: bytes) -> None:
    dump[address : address + len(data)] = data


def synthetic_dump() -> bytearray:
    dump = bytearray(DUMP_SIZE)

    wizard = layout.WIZARDS.base
    put(dump, wizard + 0x01, b"Tester\0")
    put(dump, wizard + 0x16, bytes([4]))
    put(dump, wizard + 0x356, (1234).to_bytes(2, "little"))
    put(dump, wizard + 0x25C, (567).to_bytes(2, "little"))

    city = layout.CITIES.base
    put(dump, city, b"Testburg\0")
    put(dump, city + 15, bytes([10, 20, 0, 0, 2, 5]))  # x, y, plane, owner, size, pop k
    put(dump, city + 24, (8).to_bytes(2, "little"))  # tens
    put(dump, city + 31 + 29, bytes([1]))  # granary

    put(dump, layout.UNIT_COUNT, (2).to_bytes(2, "little"))
    unit = layout.UNITS.base
    put(dump, unit, bytes([10, 20, 0, 0, 2, 39]))
    put(dump, unit + 32, bytes([10, 20, 0xFF, 0xFF, 2, 40]))  # dead

    names = layout.DGROUP + 0x1000
    put(dump, names, b"Spearmen\0")
    put(dump, layout.UNIT_TYPES.base + 39 * 0x24, (0x1000).to_bytes(2, "little"))

    node = layout.NODES.base
    put(dump, node, bytes([42, 10, 0, 0xFF, 2, 42, 43]))
    put(dump, node + 25, bytes([10, 10]))

    encounter = layout.ENCOUNTERS.base
    put(dump, encounter, bytes([42, 10, 0, 0, 3, 192, 0x80]))
    return dump


def test_check_accepts_the_synthetic_layout():
    assert layout.check(bytes(synthetic_dump())) is None


def test_check_rejects_an_empty_dump():
    assert layout.check(bytes(DUMP_SIZE)) == "wizard 0 has no readable name"


def test_decoders():
    dump = bytes(synthetic_dump())

    wizard = decode.wizards(dump)[0]
    assert (wizard["name"], wizard["gold"], wizard["mana"], wizard["banner"]) == (
        "Tester", 1234, 567, 4)

    [city] = decode.cities(dump)
    assert (city["name"], city["population"], city["size"]) == ("Testburg", 5080, 2)
    assert json.loads(city["buildings"]) == [29]

    alive, dead = decode.units(dump)
    assert (alive["type_name"], alive["dead"], dead["dead"]) == ("Spearmen", 0, 1)

    node = decode.nodes(dump)[0]
    assert (node["owner"], json.loads(node["aura"])) == (-1, [[42, 10], [43, 10]])

    encounter = decode.encounters(dump)[0]
    assert (encounter["guard1_left"], encounter["guard1_start"]) == (0, 8)


def test_store_decodes_dumps_from_the_vault(tmp_path):
    dump_path = tmp_path / "cp.bin"
    dump_path.write_bytes(bytes(synthetic_dump()))
    store = Store(Vault(tmp_path / "vault"))
    prov = Provenance("test", source="synthetic")

    first = store.ingest([dump_path], prov)
    assert [new for _, _, new in first] == [True]
    again = store.ingest([dump_path], prov)
    assert [new for _, _, new in again] == [False]
    assert store.db.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 1

    item = store.vault.catalog.db.execute("SELECT kind, storage FROM items").fetchone()
    assert (item["kind"], item["storage"]) == ("ramdump", "paged")

    assert store.rebuild() == 1
    gold = store.db.execute("SELECT gold FROM wizards WHERE idx = 0").fetchone()[0]
    assert gold == 1234


class FakeDosbox:
    url = "http://fake"

    def __init__(self, dump: bytes):
        self.dump = dump

    def memory(self) -> bytes:
        return self.dump

    def cpu_state(self) -> bytes:
        return b'{"registers": {"ss": 10399}}'

    def screenshot(self, kind: str = "raw") -> bytes:
        return b"\x89PNG fake"


def test_checkpoint_files_dump_screenshot_and_registers(tmp_path):
    store = Store(Vault(tmp_path / "vault"))
    checkpoint_id = store.checkpoint(FakeDosbox(bytes(synthetic_dump())), "Bought granary", "live")

    row = store.db.execute("SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,)).fetchone()
    assert row["name"].endswith("-bought-granary") and row["note"] == "Bought granary"
    assert row["layout_error"] is None and row["screenshot_evi_item_id"] is not None

    children = store.vault.catalog.db.execute(
        "SELECT name FROM items WHERE parent_id = ? ORDER BY name", (row["evi_item_id"],)
    ).fetchall()
    assert [c["name"].rsplit(".", 1)[-1] for c in children] == ["json", "png"]
    assert store.db.execute("SELECT gold FROM wizards").fetchone()[0] == 1234
