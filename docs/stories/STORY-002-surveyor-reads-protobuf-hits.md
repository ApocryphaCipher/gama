# STORY-002: `gama surveyor` reads protobuf hits

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs [STORY-001](STORY-001-create-the-contract-repo.md) and the fork's
[STORY-002](https://github.com/ApocryphaCipher/dosbox-staging/blob/apocrypha/research/docs/apocrypha/stories/STORY-002-signature-hits-as-protobuf.md).
**Size:** small to medium

## The idea

This is the smallest end-to-end slice of the whole epic, and the one to do
first. The Surveyor loop already works: hover a tile, the game rewrites its text
slots, a watch fires, and the hit carries the memory window and the DOS mouse
position. `surveyor.hovers()` reads those hits from JSON Lines. Teach it to read
the same hits from `hits.pb`, change nothing about the answer.

## What changes

- A reader that yields hit records from a file of length-delimited
  `SignatureHit` messages, with the same shape the rest of `surveyor.py` uses.
- `hovers()` accepts either file. Decide the dispatch: by extension (`.pb`
  against `.jsonl`) is simplest.
- The hex round-trip goes away on the protobuf path:
  `bytes.fromhex(hit["new"].replace(" ", ""))` becomes using `change.new` directly,
  since the field is `bytes`.
- `gama surveyor hits.pb` works, including `--origin`, `--plane` and `--check`.

## Acceptance

- Run the fork in `both` mode (JSON and protobuf) over the same Surveyor
  session. `gama surveyor hits.jsonl` and `gama surveyor hits.pb` print
  **identical output**, and the same `--check` tally.
- A pytest test builds a small stream of `SignatureHit` records in the test
  (synthetic, not a real log), writes it, and checks that `hovers()` returns the
  expected `Hover` values, including a bulk record being skipped, a record with
  no mouse, and a `map-view` of `0xFFFF, 0xFFFF` clearing the origin.
- The existing JSON tests still pass unchanged.
- [fork-logs-read-by-gama.md](../reference/fork-logs-read-by-gama.md) says which
  fields the protobuf path uses.

## Notes

- Today's `hovers()` skips lines with `bulk` true. In protobuf that is
  `detail` being `bulk`; the equivalent check is the oneof case.
- `new_value` is gone from the protobuf message (the fork's story drops it).
  `map-plane` uses it, so compute it from `change.new` as a little-endian number.
  That is the small piece of real logic in this story.
- The viewer should not care which format it got. If it does, the abstraction is
  in the wrong place.
