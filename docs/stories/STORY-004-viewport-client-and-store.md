# STORY-004: A viewport client that stores frames

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs the fork's
[STORY-004](https://github.com/ApocryphaCipher/dosbox-staging/blob/apocrypha/research/docs/apocrypha/stories/STORY-004-viewport-sampler-and-ring-buffer.md).
**Size:** medium

## The idea

The fork's viewport serves a small window of memory as frames, newest changes
only, from a bounded buffer. A client polls `GET /api/v1/viewport?since=SEQ`.
gama is that client: it keeps the `seq` it has seen, asks for newer frames,
and stores them so they can be queried next to the checkpoints.

## What changes

- `DosboxApi.viewport(since)` returns the decoded frames (add to
  [`dosbox.py`](../../src/gama/dosbox.py)).
- A command, say `gama watch --every 250`, polls until interrupted and stores
  each new frame. `Ctrl-C` stops it cleanly.
- Frames go in a derived table `viewport_frames`, **not** the vault: the
  Evi rule is that originals are kept, and these are a stream, so a session's
  stream is filed in the vault as one evidence item when `watch` ends
  (a length-delimited `.pb` file), and the table is derived from it. That keeps
  "gama stores no evidence" true.
- Columns: `session`, `seq`, `time`, `base`, `data`, `mouse_x`, `mouse_y`,
  `anchor`, `status`.

## Acceptance

- Against a running fork with a fixed viewport, `gama watch` stores one row per
  frame, with no duplicates and no gaps except where the fork's buffer wrapped
  (report the gap when `seq` jumps).
- When the fork isn't running or the viewport setting is off, `gama watch`
  says so and exits, rather than looping on errors.
- At the end of a session the stream is one item in the vault, with provenance
  naming the fork's URL and the viewport setting; `gama rebuild` can recreate
  `viewport_frames` from the vault.
- pytest tests use a fake server (a local `http.server` returning canned
  protobuf frames), covering a normal poll, a gap, and an empty answer.

## Notes

- Polling faster than the fork samples just returns empty answers. Poll at about
  the fork's interval.
- The fork's endpoint still answers while the game is paused, so `watch` keeps
  working through a pause-on-hit.
- Whether to also write frames straight to SQLite while polling, for live
  queries, is a choice for the story; the vault copy is the one that must
  exist.
