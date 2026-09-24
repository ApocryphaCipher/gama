"""gama's derived database, built from RAM dumps kept in an Evi vault.

Evi holds the evidence: each dump is an original, stored as shared pages
and catalogued with its provenance. gama only reads dumps out of the
vault and decodes them. Its SQLite file lives in the vault's `derived/`
folder, and `gama rebuild` can recreate it from the vault at any time.
"""

import sqlite3
from pathlib import Path

from evi.vault import Provenance, Vault

from gama import decode, layout

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY,
    evi_item_id INTEGER NOT NULL UNIQUE,  -- the dump's item in the Evi catalogue
    dump_sha256 TEXT NOT NULL,
    name TEXT NOT NULL,
    collection TEXT NOT NULL,
    taken_at TEXT,
    layout_error TEXT
);
"""


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
        self.db.executescript(SCHEMA)

    def ingest(self, paths: list[Path], prov: Provenance) -> list[tuple[int, str, bool]]:
        """Add dump files to the vault, then decode any new ones."""
        results = []
        for path in paths:
            results += self.vault.add_path(path, prov, exclude=[])
        self.index(prov.collection)
        return results

    def index(self, collection: str | None = None) -> int:
        """Decode every vault RAM dump not decoded yet. Returns how many."""
        query = (
            "SELECT id, sha256, name, collection, file_time FROM items"
            " WHERE kind = 'ramdump'" + (" AND collection = ?" if collection else "") +
            " ORDER BY file_time, id"
        )
        items = self.vault.catalog.db.execute(query, (collection,) if collection else ()).fetchall()
        known = {row[0] for row in self.db.execute("SELECT evi_item_id FROM checkpoints")}
        new = [item for item in items if item["id"] not in known]
        for item in new:
            cur = self.db.execute(
                "INSERT INTO checkpoints (evi_item_id, dump_sha256, name, collection, taken_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (item["id"], item["sha256"], item["name"].removesuffix(".bin"),
                 item["collection"], item["file_time"]),
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
