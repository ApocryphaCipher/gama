# STORY-005: Export the derived tables as protobuf

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs [STORY-001](STORY-001-create-the-contract-repo.md).
**Size:** medium

## The idea

gama's answers live in SQLite, which is good for questions and no use to a tool
that isn't Python. A `gama export` command writes a checkpoint's decoded tables
as protobuf, for another program (Mirror, in Elixir) to read without opening
SQLite or knowing gama's column names.

## What changes

- A command: `gama export CHECKPOINT -o checkpoint.pb`, writing one `Checkpoint`
  message holding the tables as repeated sub-messages.
- Messages added to the contract, as an `export.proto`:

```proto
message Checkpoint {
  string name = 1;
  string dump_sha256 = 2;
  google.protobuf.Timestamp taken_at = 3;
  repeated Wizard wizards = 4;
  repeated City cities = 5;
  repeated Unit units = 6;
  repeated Node nodes = 7;
  repeated Encounter encounters = 8;
}
```

- Each row message mirrors its table's columns
  ([derived-tables.md](../reference/derived-tables.md)). The JSON-in-a-column
  fields become real structure: `City.buildings` is a `repeated uint32`;
  `Node.aura` is `repeated Tile { uint32 x; uint32 y; }`.
- **Guesses stay guesses.** The columns marked *guess* are exported in a nested
  `Unverified` message (or carry a field option) so a consumer can't mistake
  them for checked data. This carries gama's "only checked fields" rule over
  the wire.

## Acceptance

- `gama export` on a real checkpoint writes a file a second program decodes with
  the generated code and gets the same rows as `gama sql`.
- A pytest test round-trips a synthetic dump: decode, export, parse, and compare
  to the decoder's rows.
- A checkpoint with a `layout_error` refuses to export, with the reason.
- The contract's README says that the exported messages are *not* a stable
  game-independent API: they describe Master of Magic's tables.

## Notes

- This is the one place the contract gets game-specific. Keep it in its own
  file so the fork and Evi never need it.
- Exporting with `population` as the decoded number and not the two raw fields
  loses the raw bytes; fine, they are in the dump.
