# What gama reads from the fork

gama is the consumer of the DOSBox fork's outputs. This page lists the parts
of each format gama actually depends on, so a change to the fork's format knows
what it would break. The formats themselves are described in the fork's docs:
[`docs/apocrypha/reference/`](https://github.com/ApocryphaCipher/dosbox-staging/tree/apocrypha/research/docs/apocrypha/reference).

Client code is in [`dosbox.py`](../../src/gama/dosbox.py),
[`surveyor.py`](../../src/gama/surveyor.py) and
[`filemap.py`](../../src/gama/filemap.py).

## HTTP API (`DosboxApi`, default `http://127.0.0.1:8086`)

| Call | Used for |
| --- | --- |
| `GET /api/v1/dosbox/info` | `info()`; not used by a command yet |
| `GET /api/v1/memory/0/16777216` | the 16 MB dump (`MEMORY_SIZE`), raw bytes |
| `GET /api/v1/cpu/state` | the registers, stored as `<name>.cpu.json` |
| `POST /api/v1/capture/screenshot?type=raw&inline=1` | the screenshot PNG, stored as `<name>.png`. If it fails, `gama checkpoint` says so and carries on without one |

The timeout is 30 s. A 16 MB read goes through the fork's bridge, which waits
up to 250 ms for the emulation thread to run the command; see the fork's
[http-api.md](https://github.com/ApocryphaCipher/dosbox-staging/blob/apocrypha/research/docs/apocrypha/reference/http-api.md#how-a-request-runs).

## `hits.jsonl` (`gama surveyor`)

Per line, gama uses:

| Field | How |
| --- | --- |
| `bulk` | lines with it true are skipped |
| `signature` | `map-view` and `map-plane` set state; names starting `surveyor-text` are hovers; all others are ignored |
| `new` | hex text, turned into bytes with `bytes.fromhex(hit["new"].replace(" ", ""))`. For `map-view`: two `u16` (x, y) of the view's top-left tile, where `0xFFFF, 0xFFFF` means "not on the map" |
| `old` | the same, to keep only the strings that changed |
| `new_value` | for `map-plane`, the plane |
| `mouse` | `[x, y]`, INT 33h coordinates (x 0 to 639 in the game's 320-pixel mode, so it halves x) |
| `t` | the time column |

The map view is 12 by 10 tiles of 20 by 18 pixels from screen (0, 20). A hover
text is any run of 3 or more printable ASCII bytes that changed.

The signatures that produce these are in
[`signatures/mom/`](../../signatures/mom). Names gama depends on:
`map-view`, `map-plane`, `surveyor-text`, `surveyor-text-2`.

Because gama converts the hex text back to bytes, this is the place a binary
format would remove work (see [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)).

## The file-call log (`gama filemap`)

Used per line: `op` (`read` or `write` only), `ok`, `file` (matched
case-insensitively with a glob), `position`, `done` (must be non-zero), `buffer`
and `seq`. A line with no `position` (a device) is skipped.

`merge()` joins transfers that continue each other in **both** the file and
memory: same op and file, the next file offset, and the next memory address.
`buffer - position` (`ram_minus_offset`) is constant across a block kept in one
piece in memory.
