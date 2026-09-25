"""gama command line: add dumps to the Evi vault, decode them, run SQL."""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from evi.vault import Provenance, Vault

from gama import filemap, layout, resources, surveyor
from gama.dosbox import DEFAULT_URL, DosboxApi
from gama.store import Store


def cmd_ingest(store: Store, args: argparse.Namespace) -> None:
    paths = sorted(
        (p for arg in args.paths
         for p in (Path(arg).glob("*.bin") if Path(arg).is_dir() else [Path(arg)])),
        key=lambda p: p.stat().st_mtime,
    )
    prov = Provenance(args.collection, args.source, None, args.license, args.note)
    results = store.ingest(paths, prov)
    new = sum(was_new for _, _, was_new in results)
    print(f"{new} dumps added to the vault, {len(results) - new} already there")
    cmd_status(store, args)


def cmd_checkpoint(store: Store, args: argparse.Namespace) -> None:
    collection = args.collection or f"mom-live-{date.today().isoformat()}"
    checkpoint_id = store.checkpoint(DosboxApi(args.url), args.label, collection, args.note)
    row = store.db.execute(
        "SELECT name, screenshot_evi_item_id, layout_error FROM checkpoints WHERE id = ?",
        (checkpoint_id,),
    ).fetchone()
    shot = "with screenshot" if row["screenshot_evi_item_id"] else "no screenshot"
    status = f"not decoded: {row['layout_error']}" if row["layout_error"] else "decoded"
    print(f"checkpoint {checkpoint_id}  {row['name']}  ({collection}, {shot}, {status})")


def cmd_filemap(_store: Store | None, args: argparse.Namespace) -> None:
    items = filemap.merge(filemap.transfers(Path(args.log), args.file, args.op))
    print("seq\top\tfile\tfile_offset\tlength\tram_address\tram_minus_offset")
    for t in items:
        print(f"{t.seq}\t{t.op}\t{t.file}\t0x{t.position:06X}\t{t.length}\t0x{t.buffer:06X}\t0x{t.delta:X}")


# The overland map view: 12 x 10 tiles of 20 x 18 pixels from screen (0, 20);
# INT 33h reports x in 0..639 in MoM's 320-pixel mode. The world wraps at x = 60.
def cmd_surveyor(_store: Store | None, args: argparse.Namespace) -> None:
    origin = tuple(int(v) for v in args.origin.split(",")) if args.origin else None
    world = None
    if args.check:
        data = Path(args.check).read_bytes()
        world = resources.Map(layout.ram_from_save(data) if len(data) == layout.SAVE_SIZE else data)
    counts = {}
    print("time\tmouse\ttile\tplane\t" + ("check\t" if world else "") + "text")
    for hover in surveyor.hovers(Path(args.hits), origin, args.plane):
        verdict = ""
        if world and hover.tile and hover.plane is not None:
            verdict = surveyor.check(world, hover)
            counts[verdict] = counts.get(verdict, 0) + 1
            verdict += "\t"
        elif world:
            verdict = "\t"
        plane = "" if hover.plane is None else hover.plane
        print(f"{hover.time[11:19]}\t{list(hover.mouse or [])}\t{hover.tile or ''}\t{plane}\t{verdict}{' | '.join(hover.texts)}")
    if world:
        print("# " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), file=sys.stderr)


def cmd_resources(_store: Store | None, args: argparse.Namespace) -> None:
    data = Path(args.dump).read_bytes()
    if len(data) == layout.SAVE_SIZE:
        data = layout.ram_from_save(data)
    result = resources.city_resources(data, args.x, args.y, args.plane)
    print(f"Maximum Pop {result.max_pop}, Prod Bonus +{result.production}%, Gold Bonus +{result.gold}%")
    print("  " + ", ".join(f"{k} {v}" for k, v in result.notes.items()))


def cmd_index(store: Store, args: argparse.Namespace) -> None:
    print(f"Decoded {store.index(args.collection)} new dumps")
    cmd_status(store, args)


def cmd_rebuild(store: Store, _args: argparse.Namespace) -> None:
    print(f"Decoded {store.rebuild()} checkpoints again")


def cmd_status(store: Store, _args: argparse.Namespace) -> None:
    rows = store.db.execute(
        "SELECT collection, count(*) AS n, sum(layout_error IS NOT NULL) AS failed"
        " FROM checkpoints GROUP BY collection"
    )
    for row in rows:
        failed = f", {row['failed']} not decoded" if row["failed"] else ""
        print(f"{row['collection']}: {row['n']} checkpoints{failed}")


def cmd_sql(store: Store, args: argparse.Namespace) -> None:
    cur = store.db.execute(args.query)
    if cur.description is None:
        store.db.commit()
        return
    print("\t".join(d[0] for d in cur.description))
    for row in cur:
        print("\t".join("" if v is None else str(v) for v in row))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gama", description="Decode game RAM dumps kept in an Evi vault")
    parser.add_argument("--home", type=Path, help="Evi vault directory (default $EVI_HOME)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="add RAM dumps (files or folders of *.bin) to the vault and decode them")
    p.add_argument("paths", nargs="+")
    p.add_argument("--collection", required=True, help="the Evi collection they belong to")
    p.add_argument("--source", help="where they came from")
    p.add_argument("--license", help="what may be done with them")
    p.add_argument("--note")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("checkpoint", help="capture memory, a screenshot and registers from the running DOSBox")
    p.add_argument("label", help="what this moment is, e.g. 'bought granary'")
    p.add_argument("--note", help="more about what was on screen")
    p.add_argument("--collection", help="Evi collection (default mom-live-<today>)")
    p.add_argument("--url", default=DEFAULT_URL, help=f"DOSBox API (default {DEFAULT_URL})")
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("filemap", help="map file offsets to memory from the DOSBox fork's file-call log")
    p.add_argument("log", help="the JSON Lines file named by webserver_file_log")
    p.add_argument("--file", default="*", help="file name glob, e.g. 'SAVE*.GAM'")
    p.add_argument("--op", choices=["read", "write"], help="only reads or only writes")
    p.set_defaults(func=cmd_filemap, needs_vault=False)

    p = sub.add_parser("surveyor", help="list the Surveyor texts and mouse positions from a signature hit log")
    p.add_argument("hits", help="hits.jsonl written by the DOSBox fork")
    p.add_argument("--origin", help="map view top-left tile 'x,y' until a map-view hit says otherwise")
    p.add_argument("--plane", type=int, help="plane (0 Arcanus, 1 Myrror) until a map-plane hit says otherwise")
    p.add_argument("--check", metavar="DUMP", help="check each hover's food and production text against this dump or save")
    p.set_defaults(func=cmd_surveyor, needs_vault=False)

    p = sub.add_parser("resources", help="the Surveyor's City Resources for a tile, from a RAM dump or save file")
    p.add_argument("dump", help="a raw RAM dump (.bin) or a save file (SAVEn.GAM)")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("plane", type=int, nargs="?", default=0, help="0 Arcanus (default), 1 Myrror")
    p.set_defaults(func=cmd_resources, needs_vault=False)

    p = sub.add_parser("index", help="decode RAM dumps already in the vault")
    p.add_argument("--collection", help="only this collection")
    p.set_defaults(func=cmd_index)

    sub.add_parser("rebuild", help="re-decode every checkpoint").set_defaults(func=cmd_rebuild)
    sub.add_parser("status", help="checkpoints per collection").set_defaults(func=cmd_status)

    p = sub.add_parser("sql", help="run a SQL query against the decoded tables")
    p.add_argument("query")
    p.set_defaults(func=cmd_sql)

    args = parser.parse_args(argv)
    if not getattr(args, "needs_vault", True):
        args.func(None, args)
        return
    home = args.home or (Path(os.environ["EVI_HOME"]) if "EVI_HOME" in os.environ else None)
    if home is None:
        sys.exit("gama: say which vault: set EVI_HOME or pass --home")
    store = Store(Vault(home))
    try:
        args.func(store, args)
    except Exception as e:  # show a clean message on the command line
        sys.exit(f"gama: {e}")


if __name__ == "__main__":
    main()
