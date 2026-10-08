# STORY-003: `gama filemap` reads the protobuf file-call log

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs [STORY-001](STORY-001-create-the-contract-repo.md) and the fork's
[STORY-003](https://github.com/ApocryphaCipher/dosbox-staging/blob/webserver-write-guard/docs/apocrypha/stories/STORY-003-file-calls-as-protobuf.md).
**Size:** small

## The idea

`filemap.transfers()` reads a JSON Lines file of DOS file calls and keeps the
reads and writes that moved bytes between a file and memory. Give it the same
second front door as [STORY-002](STORY-002-surveyor-reads-protobuf-hits.md).

## What changes

- Read length-delimited `FileCall` records and yield the same `Transfer` values.
- Keep the filter: only `READ` and `WRITE`, `ok`, with a `position` and a non-zero
  `done`, and the file glob matched case-insensitively.
- Here `optional` earns its keep. A `position` of 0 is a real file offset, and
  the Python filter must test presence (`HasField("position")`), not truthiness.
  Today's JSON code gets this right with `"position" not in call`; the protobuf
  version must preserve it. This is the thing to test.

## Acceptance

- On the same save-and-load session logged in both formats, `gama filemap` prints
  **the same table** for `--file 'SAVE*.GAM' --op write` from either file.
- A pytest test covers a write at file offset 0 (it must appear), a device read
  with no `position` (it must not), and a failed call (it must not). Synthetic
  records only.
- `merge()` is untouched: it works on `Transfer`, not on the file format.

## Notes

- This story is small on purpose. If it takes longer than STORY-002, the
  abstraction from that story is wrong.
