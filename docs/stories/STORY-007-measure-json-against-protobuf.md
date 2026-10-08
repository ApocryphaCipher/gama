# STORY-007: Measure JSON against protobuf

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started. Needs STORY-002 and STORY-003.
**Size:** small

## The idea

The epic argues that protobuf makes the logs smaller and easier to read, but
also says JSON is fast enough. Settle it with numbers from real logs, so the
epic's claims are checked and not guessed. (Mirror's rule: ground every claim in
the real files, and mark guesses as guesses.)

## What to measure

On the same Surveyor session logged in both formats (the fork's `both` mode),
and the same save-and-load file-call log:

| Measure | How |
| --- | --- |
| file size | bytes of `hits.jsonl` against `hits.pb`, and of the file-call logs |
| size compressed | both, with zstd (what the vault would store) |
| read time | time for `gama surveyor` / `gama filemap` on each, best of several runs, same machine |
| record count | identical in both, as a sanity check |

*Guess to check:* hex text is three characters per byte, so `window`, `old` and
`new` should shrink to about a third, and the whole file by somewhat less. Compression
may close most of the gap, because hex text compresses well. Whether it does is the
interesting result.

## Acceptance

- A note in `docs/notes/` with the table of numbers, the date, the machine and
  the commands used, so someone can repeat it.
- The epic and the fork's STORY-002 are updated with the real figures where they
  currently say "expect".
- If protobuf turns out not to help in size or time, say so plainly. The epic's
  other reasons (a contract, no hex parsing, a second language) still stand on
  their own.

## Notes

- The logs hold a game's memory. The note records sizes and times only; never
  paste log content.
