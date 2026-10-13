# STORY-008: Mirror reads gama's export

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs [STORY-005](STORY-005-export-derived-tables-as-protobuf.md).
**Size:** medium, **in the Mirror repository**

This story is recorded here because gama's export is what it reads. It would
be done under Mirror's own rules (its AGENTS.md), not gama's.

## The idea

Mirror, the Phoenix/LiveView save viewer, can show a save file. With gama's
export it could also show a *live game's* state from a checkpoint: cities,
units, nodes, encounters, as of the moment captured. It would read the
protobuf file with the Elixir `protobuf` package.

## Before anything else

- **Mirror's AGENTS.md §4: no new Hex dependency without Kevin's approval.**
  This story needs one (`protobuf`, and `protoc-gen-elixir` for generating the
  modules). Ask first; "no" is a fine answer and ends the story.
- Check whether `jason` and pattern matching already do the job. For *this*
  format they do not, but §4 asks the question, so answer it in writing.

## What changes in Mirror

- Generated modules from the same `.proto` files (the pinned contract repo).
- A module `Mirror.Checkpoint` that reads a `Checkpoint` file and returns
  `{:ok, value}` or `{:error, reason}`. Never raises on bad data (AGENTS.md §7).
- Possibly a map overlay fed from a checkpoint instead of a save. Out of scope
  for this story; it only has to read the file and show it can.

## Acceptance

- Mirror reads a file written by `gama export` and exposes the same rows
  gama's SQLite holds. A test uses a **synthetic** file built in the test.
- Mirror's own checks pass: `mix format --check-formatted`,
  `mix compile --warnings-as-errors`, `mix test`.
- A Mirror story and epic link are added in Mirror's `docs/stories/`, per its
  rule that ideas become tickets there.

## Notes

- Elixir pattern matching suits protobuf's wire format well, so a hand-written
  decoder for one or two messages is a legitimate alternative to a dependency.
  Worth saying in the approval request.
