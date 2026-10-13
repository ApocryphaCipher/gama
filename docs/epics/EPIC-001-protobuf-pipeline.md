# EPIC-001: A protobuf pipeline

**Status:** Proposed (2026-10-08). Not started.
**Requested by:** [Kevin](https://github.com/KevinAsbury), 2026-10-08, "for funsies":
a play project turning the Apocrypha tools into protobuf versions.
**Sibling epics:** [fork EPIC-001](https://github.com/ApocryphaCipher/dosbox-staging/blob/apocrypha/research/docs/apocrypha/epics/EPIC-001-protobuf-output.md),
[Evi EPIC-001](https://github.com/ApocryphaCipher/evi/blob/main/docs/epics/EPIC-001-protobuf-export.md)

## Goal

Make gama the middle of a typed pipeline: read what the fork emits as protobuf
(falling back to JSON), and hand structured data on to other tools, namely
Mirror and Evi, as protobuf too. Along the way, build the one thing the three
tools should share: **a written contract** of the messages between them.

This is a learning and tidiness project. At this volume JSON is fast enough.
The gains worth having:

- the formats between the tools stop living in code and prose;
- gama's hex-text parsing disappears (`bytes.fromhex(hit["new"].replace(" ", ""))`
  in `surveyor.py` exists only because JSON can't carry bytes);
- an Elixir tool (Mirror) reads what a Python tool wrote, from one schema.

## Decisions made

- **JSON keeps working.** gama reads both formats; the protobuf path is added,
  not swapped in.
- **Package `apocrypha.v1`**, files length-delimited (varint length, then the
  message), HTTP bodies `application/x-protobuf`. Names are proposals until a
  story is done.
- **One contract, in one place.** The `.proto` files live in a shared repo
  (working name `apocrypha-proto`) that the fork, gama and Evi each pin to a
  version. [STORY-001](../stories/STORY-001-create-the-contract-repo.md) decides
  and creates it.
- **Lint and breaking-change checks with Buf**, so the compatibility rules
  (never renumber or reuse a field; `reserved` for removed ones) are enforced
  by a tool, not by memory.
- **Game-agnostic messages.** Nothing in the contract names a game. A city is
  a Master of Magic idea; "a table of records at an address" is not.

## Stories, in order

1. [STORY-001](../stories/STORY-001-create-the-contract-repo.md): create the contract repo, with Buf lint and breaking checks
2. [STORY-002](../stories/STORY-002-surveyor-reads-protobuf-hits.md): `gama surveyor` reads `hits.pb`
3. [STORY-003](../stories/STORY-003-filemap-reads-protobuf-file-calls.md): `gama filemap` reads the protobuf file-call log
4. [STORY-007](../stories/STORY-007-measure-json-against-protobuf.md): measure JSON against protobuf (after 002 and 003, so there is something to measure)
5. [STORY-004](../stories/STORY-004-viewport-client-and-store.md): a viewport client that stores frames
6. [STORY-005](../stories/STORY-005-export-derived-tables-as-protobuf.md): export the derived tables as protobuf
7. [STORY-008](../stories/STORY-008-mirror-reads-the-export.md): Mirror reads the export (lives in Mirror; needs Kevin's approval for a dependency)
8. [STORY-006](../stories/STORY-006-stream-over-grpc.md): stream checkpoints and hits over gRPC (stretch)

The numbers are story ids and stay put; the order above is the order to do
them in.

## Out of scope

- Replacing SQLite as the place to ask questions. The derived database stays.
- Putting protobuf *in* the Evi vault format (that is Evi's epic, and a
  separate decision).
- Anything that makes gama depend on the fork's source tree.

## Risks

- **Python 3.14 and protobuf.** gama requires Python ≥ 3.14. Check the `protobuf`
  package supports it before starting; if not, that is the first thing the first
  story reports.
- **Two dependencies on the contract.** If the fork, gama and Evi each vendor a
  copy of the `.proto` files, they drift. Pin one source.
- **Generated code in the repo?** Either commit it (simple, noisy diffs) or
  generate at build time (clean, needs `protoc` or Buf for every contributor).
  STORY-001 decides.
