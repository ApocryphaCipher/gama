# Backlog

Unsorted, not yet promoted to a story. Each item says how it was found.

- **`signatures/mom/hits.jsonl` is game memory sitting in the source tree.**
  It is 9,839 lines (checked 2026-10-08), git-ignored, so it won't be committed
  by accident, but it is still a log of a game's own memory next to the code.
  File it in the Evi vault (`evi add`) and remove it from the tree. Not done
  here: it is the only copy.
- **A decoded table doesn't exist until a dump has rows for it.**
  `Store._decode()` creates each table from the first non-empty result, so on
  an empty vault, `gama sql "SELECT ... FROM cities"` says "no such table". Create
  the tables from the column lists up front. *Found reading `store.py`.*
- **`DosboxApi.info()` is unused.** Either use it (check the fork's version on
  `gama checkpoint` and record it in the item's note) or delete it.
- **Two wordings for the dump licence.** The README example uses
  `--license "game data: never publish raw"`; `gama checkpoint` records
  `game data: never publish raw dumps; short excerpts are fine`. Pick one.
- **A save file cannot go through the full decoder.** `ram_from_save()`
  places only wizards, terrain, cities, minerals, explored and terrain flags,
  so units, nodes and encounters are missing. Mirror decodes those from saves in
  its own way. Whether gama should too is a decision, not a bug.
- **The Surveyor check compares text fragments.** `surveyor.check()` can
  report agreement and conflict but, as its docstring says, cannot prove a
  single hover (the text slots are reused). Fine; don't over-claim it.
