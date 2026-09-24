"""gama's derived database, built from RAM dumps kept in an Evi vault.

Evi holds the evidence: each dump is an original, stored as shared pages
and catalogued with its provenance. gama only reads dumps out of the
vault and decodes them. Its SQLite file lives in the vault's `derived/`
folder, and `gama rebuild` can recreate it from the vault at any time.
"""

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from evi.vault import Provenance, Vault

from gama import decode, layout

SCHEMA_VERSION = 2  # bump when the tables change; the derived db is then rebuilt

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY,
    evi_item_id INTEGER NOT NULL UNIQUE,  -- the dump's item in the Evi catalogue
    dump_sha256 TEXT NOT NULL,
    name TEXT NOT NULL,
    collection TEXT NOT NULL,
    taken_at TEXT,
    note TEXT,                            -- what was on screen
    screenshot_evi_item_id INTEGER,       -- a screenshot taken with the dump, if any
    layout_error TEXT
);
"""

DUMP_LICENSE = "game data: never publish raw dumps; short excerpts are fine"
CAPTURE_LICENSE = "our capture of the game: fine to use in reports"


def _decoded_table_sql(table: str, columns: list[str]) -> str:
    cols = ", ".join(columns)
    return (
        f"CREATE TABLE IF NOT EXISTS {table} ("
        f"checkpoint_id INTEGER NOT NULL REFERENCES checkpoints(id), {cols})"
    )


class Store:
    def __init__(self, vault: Vault):
        self.vault = vault
        derived = vault.home / "derived"
        derived.mkdir(exist_ok=True)
        self.db = sqlite3.connect(derived / "gama.sqlite")
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            # Everything here is derived from the vault, so rebuild from scratch.
            for table in ["checkpoints", *decode.TABLES]:
                self.db.execute(f"DROP TABLE IF EXISTS {table}")
            self.db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.db.executescript(SCHEMA)

    def ingest(self, paths: list[Path], prov: Provenance) -> list[tuple[int, str, bool]]:
        """Add dump files to the vault, then decode any new ones."""
        results = []
        for path in paths:
            results += self.vault.add_path(path, prov, exclude=[])
        self.index(prov.collection)
        return results

    def checkpoint(self, api, label: str, collection: str, note: str | None = None) -> int:
        """Capture memory, a raw screenshot and the CPU registers from the
        running DOSBox, file them in the vault, and decode the dump.
        Returns the new checkpoint's id."""
        taken_at = datetime.now(UTC).isoformat(timespec="seconds")
        stamp = taken_at.replace(":", "").replace("-", "").removesuffix("+0000")
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        name = f"{stamp}-{slug}"
        what = label + (f": {note}" if note else "")
        source = f"DOSBox fork API at {api.url}"

        memory = api.memory()
        dump_id = self.vault.add_bytes(
            memory, f"{name}.bin", f"{api.url}/api/v1/memory/0/{len(memory)} @ {taken_at}",
            Provenance(collection, source, None, DUMP_LICENSE, what), file_time=taken_at,
        )
        captured = Provenance(collection, source, None, CAPTURE_LICENSE, what)
        self.vault.add_bytes(
            api.cpu_state(), f"{name}.cpu.json", f"{api.url}/api/v1/cpu/state @ {taken_at}",
            captured, parent_id=dump_id, file_time=taken_at,
        )
        try:
            screenshot = api.screenshot("raw")
        except Exception as e:  # an older DOSBox build has no screenshot endpoint
            print(f"gama: no screenshot ({e})")
        else:
            self.vault.add_bytes(
                screenshot, f"{name}.png", f"{api.url}/api/v1/capture/screenshot?type=raw @ {taken_at}",
                captured, parent_id=dump_id, file_time=taken_at,
            )

        self.index(collection)
        return self.db.execute(
            "SELECT id FROM checkpoints WHERE evi_item_id = ?", (dump_id,)
        ).fetchone()[0]

    def index(self, collection: str | None = None) -> int:
        """Decode every vault RAM dump not decoded yet. Returns how many."""
        query = (
            "SELECT id, sha256, name, collection, file_time, note FROM items"
            " WHERE kind = 'ramdump'" + (" AND collection = ?" if collection else "") +
            " ORDER BY file_time, id"
        )
        items = self.vault.catalog.db.execute(query, (collection,) if collection else ()).fetchall()
        known = {row[0] for row in self.db.execute("SELECT evi_item_id FROM checkpoints")}
        new = [item for item in items if item["id"] not in known]
        for item in new:
            screenshot = self.vault.catalog.db.execute(
                "SELECT id FROM items WHERE parent_id = ? AND kind = 'image' ORDER BY id LIMIT 1",
                (item["id"],),
            ).fetchone()
            cur = self.db.execute(
                "INSERT INTO checkpoints (evi_item_id, dump_sha256, name, collection, taken_at,"
                " note, screenshot_evi_item_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (item["id"], item["sha256"], item["name"].removesuffix(".bin"),
                 item["collection"], item["file_time"], item["note"],
                 screenshot["id"] if screenshot else None),
            )
            self._decode(cur.lastrowid, self.vault.original(item["id"]))
        self.db.commit()
        return len(new)

    def rebuild(self) -> int:
        """Drop every decoded table and decode all checkpoints again."""
        for table in decode.TABLES:
            self.db.execute(f"DROP TABLE IF EXISTS {table}")
        rows = self.db.execute("SELECT id, evi_item_id FROM checkpoints").fetchall()
        for row in rows:
            self._decode(row["id"], self.vault.original(row["evi_item_id"]))
        self.db.commit()
        return len(rows)

    def _decode(self, checkpoint_id: int, data: bytes) -> None:
        error = layout.check(data)
        self.db.execute(
            "UPDATE checkpoints SET layout_error = ? WHERE id = ?", (error, checkpoint_id)
        )
        if error:
            return
        for table, decoder in decode.TABLES.items():
            rows = decoder(data)
            if not rows:
                continue
            columns = list(rows[0])
            self.db.execute(_decoded_table_sql(table, columns))
            placeholders = ", ".join("?" * (len(columns) + 1))
            self.db.executemany(
                f"INSERT INTO {table} (checkpoint_id, {', '.join(columns)})"
                f" VALUES ({placeholders})",
                [(checkpoint_id, *row.values()) for row in rows],
            )
