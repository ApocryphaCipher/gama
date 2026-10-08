# STORY-001: Create the shared contract repo

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started
**Size:** small to medium

## The idea

Three tools (the fork in C++, gama in Python, Evi in Python) and later Mirror
(Elixir) need to agree on message shapes. A protobuf contract is only a
contract if there is exactly one copy. Make a small repo that holds the `.proto`
files, lints them and guards against breaking changes, and let the others pin it.

## Decisions to make first

Write each one down in this story when it's made.

1. **Where does it live?** Working name `apocrypha-proto` under the
   `ApocryphaCipher` GitHub organisation. *Alternative:* a `proto/` folder in
   gama (it is the middle of the pipeline). Separate is cleaner for the fork and
   Evi, which shouldn't depend on gama.
2. **How do consumers get it?** A git submodule, a pinned git dependency, or
   a release tarball of generated code. gama already pulls Evi with
   `[tool.uv.sources] evi = { git = ... }`, so a git dependency is the house style.
3. **Generated code: committed or built?** Committed Python is simple but noisy;
   built needs `protoc` or `buf` for every contributor. For a one-person project,
   *guess:* commit it, with a CI check that it is up to date.
4. **Does `protobuf` support Python 3.14?** gama requires 3.14. Check the
   package before building anything on it; report here if it doesn't.

## What the first version holds

Only what a later story needs, nothing speculative:

- `apocrypha/v1/common.proto`: `Mouse`, a timestamp use, an `Anchor` enum.
- `apocrypha/v1/hit.proto`: `SignatureHit` (see the fork's
  [STORY-002](https://github.com/ApocryphaCipher/dosbox-staging/blob/webserver-write-guard/docs/apocrypha/stories/STORY-002-signature-hits-as-protobuf.md)).
- `apocrypha/v1/filecall.proto`: `FileCall` (the fork's STORY-003).
- `apocrypha/v1/viewport.proto`: `Viewport` (the fork's STORY-004).

Later stories add the exported tables (STORY-005 here) and Evi's claims (Evi
STORY-001).

## Acceptance

- The repo builds with `buf lint` and `buf breaking --against` the previous tag.
- A tag (say `v0.1.0`) exists and gama's `pyproject.toml` can depend on it.
- A README explains the rules: never renumber or reuse a field number; mark a
  removed field `reserved`; add fields freely; don't change a field's type.
- A tiny round-trip test: encode a `SignatureHit` in Python, decode it in
  Python, and check the fields. (A test in another language comes with the
  fork's own work.)
- The fork's and Evi's epics are updated with where the contract lives.

## Notes

- Keep messages game-agnostic. If a message needs a game's idea, it belongs in
  gama's own code, not in the contract.
- Field numbers 1 to 15 take one byte for the key. Give the fields that appear
  in every record (the common ones) the low numbers.
