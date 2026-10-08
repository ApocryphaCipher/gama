# gama docs

**Picking this up? Read [notes/2026-10-08-handoff.md](notes/2026-10-08-handoff.md) first.**
For what gama is and how to run it, see the [README](../README.md).

Working docs for gama (game analytics, part of **ApocryphaCipher**): the
decoding and data layer between the
[DOSBox fork](https://github.com/ApocryphaCipher/dosbox-staging/tree/webserver-write-guard),
which captures the running machine, and [Evi](https://github.com/ApocryphaCipher/evi),
which keeps the evidence. Not shipped; this is planning and reference scaffolding.

- [`reference/`](reference): what gama does *now*, checked against the code
  - [derived-tables.md](reference/derived-tables.md): every column of the SQLite tables, and which are guesses
  - [ram-layout.md](reference/ram-layout.md): where Master of Magic keeps its tables in a dump
  - [checkpoint-flow.md](reference/checkpoint-flow.md): what `gama checkpoint` files and where
  - [fork-logs-read-by-gama.md](reference/fork-logs-read-by-gama.md): which parts of the fork's formats gama depends on
- [`epics/`](epics): large bodies of work, one file each, status at the top
- [`stories/`](stories): units of work, indexed in [stories/README.md](stories/README.md)
- [`backlog.md`](backlog.md): unsorted ideas and known issues
- [`notes/`](notes): dated session notes; the newest handoff is the entry point

## Rules gama keeps

- **gama stores no evidence.** Dumps live in an Evi vault; gama reads them from there.
- **Its tables are derived**, and can always be rebuilt (`gama rebuild`).
- **Only checked fields are decoded.** A column is either checked against the
  running game or marked as a guess, here and in the code.
- **Ground every claim about the game's memory in the real thing**: a dump, a
  save, a screenshot. A layout counts as verified with two independent sources,
  or one source plus a visual check. Mark guesses as guesses and say what would
  confirm them.
- **No game data in the repo.** Dumps, saves, screenshots and `hits.jsonl` are
  evidence, not source. `hits.jsonl` is git-ignored; keep it that way.
- **Done means checked:** `uv run pytest` passes. Add a test that fails
  without a fix; build synthetic dumps in the test, never commit a real one.
- **Docs are product surface.** When behaviour changes, change the page that
  describes it in the same change.

Requires Python 3.14 or later (`requires-python = ">=3.14"`); Evi is pulled from
its GitHub repository (`[tool.uv.sources]` in `pyproject.toml`).
