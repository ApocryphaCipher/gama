"""The gama store: raw dumps kept as evidence, plus decoded SQLite tables.

Raw dumps are never replaced by decoded data. Each is stored once,
zstd-compressed and named by its SHA-256, and every decoded table can be
rebuilt from those blobs (`gama rebuild`) whenever a decoder improves.
"""

import hashlib
import sqlite3
from compression import zstd
from datetime import UTC, datetime
from pathlib import Path

from gama import decode, layout

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    taken_at TEXT NOT NULL,
    dump_sha256 TEXT NOT NULL UNIQUE,
    screenshot TEXT,
    note TEXT,
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
    def __init__(self, home: Path):
        self.home = home
        self.blobs = home / "blobs"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(home / "gama.sqlite")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def blob_path(self, sha: str) -> Path:
        return self.blobs / sha[:2] / f"{sha}.zst"

    def put_blob(self, data: bytes) -> str:
        sha = hashlib.sha256(data).hexdigest()
        path = self.blob_path(sha)
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(zstd.compress(data, level=10))
            tmp.rename(path)
        return sha

    def get_blob(self, sha: str) -> bytes:
        return zstd.decompress(self.blob_path(sha).read_bytes())

    def ingest(
        self,
        dump_path: Path,
        name: str | None = None,
        screenshot: str | None = None,
        note: str | None = None,
    ) -> tuple[int, bool]:
        """Store a dump and decode it. Returns (checkpoint id, was new)."""
        data = dump_path.read_bytes()
        sha = self.put_blob(data)
        existing = self.db.execute(
            "SELECT id FROM checkpoints WHERE dump_sha256 = ?", (sha,)
        ).fetchone()
        if existing:
            return existing["id"], False

        taken_at = datetime.fromtimestamp(dump_path.stat().st_mtime, UTC).isoformat()
        cur = self.db.execute(
            "INSERT INTO checkpoints (name, taken_at, dump_sha256, screenshot, note)"
            " VALUES (?, ?, ?, ?, ?)",
            (name or dump_path.stem, taken_at, sha, screenshot, note),
        )
        checkpoint_id = cur.lastrowid
        self._decode(checkpoint_id, data)
        self.db.commit()
        return checkpoint_id, True

    def rebuild(self) -> int:
        """Drop every decoded table and decode all stored dumps again."""
        for table in decode.TABLES:
            self.db.execute(f"DROP TABLE IF EXISTS {table}")
        rows = self.db.execute("SELECT id, dump_sha256 FROM checkpoints").fetchall()
        for row in rows:
            self._decode(row["id"], self.get_blob(row["dump_sha256"]))
        self.db.commit()
        return len(rows)

    def _decode(self, checkpoint_id: int, data: bytes) -> None:
        error = layout.check(data)
        self.db.execute(
            "UPDATE checkpoints SET layout_error = ? WHERE id = ?",
            (error, checkpoint_id),
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
