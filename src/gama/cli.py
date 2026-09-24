"""gama command line: ingest dumps, rebuild tables, run SQL."""

import argparse
import os
import sys
from pathlib import Path

from gama.store import Store

DEFAULT_HOME = Path.home() / ".mirror" / "dev" / "DOSbox" / "gama"


def _home() -> Path:
    return Path(os.environ.get("GAMA_HOME", DEFAULT_HOME))


def cmd_ingest(store: Store, args: argparse.Namespace) -> None:
    paths = sorted(
        (p for arg in args.paths for p in (Path(arg).glob("*.bin") if Path(arg).is_dir() else [Path(arg)])),
        key=lambda p: p.stat().st_mtime,
    )
    for path in paths:
        checkpoint_id, new = store.ingest(path, name=args.name, note=args.note)
        error = store.db.execute(
            "SELECT layout_error FROM checkpoints WHERE id = ?", (checkpoint_id,)
        ).fetchone()[0]
        status = "added" if new else "already stored"
        if error:
            status += f", not decoded: {error}"
        print(f"{checkpoint_id:4}  {path.name}  ({status})")


def cmd_rebuild(store: Store, _args: argparse.Namespace) -> None:
    print(f"Decoded {store.rebuild()} checkpoints again")


def cmd_sql(store: Store, args: argparse.Namespace) -> None:
    cur = store.db.execute(args.query)
    if cur.description is None:
        store.db.commit()
        return
    names = [d[0] for d in cur.description]
    print("\t".join(names))
    for row in cur:
        print("\t".join("" if v is None else str(v) for v in row))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gama", description=__doc__)
    parser.add_argument("--home", type=Path, help=f"data directory (default {DEFAULT_HOME})")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="store and decode RAM dumps (files or folders of *.bin)")
    ingest.add_argument("paths", nargs="+")
    ingest.add_argument("--name", help="checkpoint name (default: the file name)")
    ingest.add_argument("--note", help="what was on screen")
    ingest.set_defaults(func=cmd_ingest)

    sub.add_parser("rebuild", help="re-decode every stored dump").set_defaults(func=cmd_rebuild)

    sql = sub.add_parser("sql", help="run a SQL query against the database")
    sql.add_argument("query")
    sql.set_defaults(func=cmd_sql)

    args = parser.parse_args(argv)
    store = Store(args.home or _home())
    try:
        args.func(store, args)
    except Exception as e:  # show a clean message on the command line
        sys.exit(f"gama: {e}")


if __name__ == "__main__":
    main()
