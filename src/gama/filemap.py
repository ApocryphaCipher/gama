"""Read the DOSBox fork's DOS file-call log (JSON Lines) and map file
offsets to the memory the bytes came from or went to.

When the game saves, it writes each block of the save file straight from
where that block lives in memory. So the writes to `SAVEn.GAM`, in order,
give every block's file offset, length and RAM address, and a load (reads
of the same file) should mirror it.
"""

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Transfer:
    seq: int
    op: str  # read or write
    file: str
    position: int  # file offset
    length: int  # bytes actually moved
    buffer: int  # physical memory address

    @property
    def delta(self) -> int:
        """buffer - position: constant across a block kept in one piece."""
        return self.buffer - self.position


def transfers(log: Path, file_glob: str = "*", op: str | None = None) -> list[Transfer]:
    result = []
    for line in log.read_text().splitlines():
        call = json.loads(line)
        if call.get("op") not in ("read", "write") or not call.get("ok"):
            continue
        if op and call["op"] != op:
            continue
        if not fnmatch.fnmatch(call.get("file", "").upper(), file_glob.upper()):
            continue
        if "position" not in call or not call.get("done"):
            continue
        result.append(Transfer(call["seq"], call["op"], call["file"], call["position"],
                               call["done"], call["buffer"]))
    return result


def merge(items: list[Transfer]) -> list[Transfer]:
    """Join transfers that continue each other in both the file and memory
    (a block written in several calls)."""
    merged: list[Transfer] = []
    for t in items:
        last = merged[-1] if merged else None
        if (last and last.op == t.op and last.file == t.file
                and last.position + last.length == t.position
                and last.buffer + last.length == t.buffer):
            merged[-1] = Transfer(last.seq, last.op, last.file, last.position,
                                  last.length + t.length, last.buffer)
        else:
            merged.append(t)
    return merged
