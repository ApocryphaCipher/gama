# STORY-006: Stream checkpoints and hits over gRPC

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-pipeline.md)
**Status:** Not started, stretch. Needs STORY-002, STORY-004 and STORY-005.
**Size:** large

## The idea

So far every handoff is a file or a poll. The protobuf way to *push* is gRPC:
a service where a consumer subscribes and gets messages as they happen. This is
the fun end of the epic: hover a tile in the Surveyor and watch another program
update.

## What changes

A long-running `gama serve` (localhost only, as the fork is) with a gRPC
service, working name:

```proto
service Gama {
  rpc WatchHits(WatchRequest) returns (stream SignatureHit);
  rpc WatchViewport(WatchRequest) returns (stream Viewport);
  rpc GetCheckpoint(CheckpointRequest) returns (Checkpoint);
}
```

`WatchHits` tails the fork's hit file (or its protobuf stream) and forwards each
record; `WatchViewport` re-serves what STORY-004 polls; `GetCheckpoint` is the
export from STORY-005 on demand.

## Decisions to make first

1. **Python gRPC on 3.14.** Check `grpcio` supports it, as for `protobuf` in
   [STORY-001](STORY-001-create-the-contract-repo.md).
2. **Is gama the right place?** An alternative is a thin service in Evi or a new
   repo. gama is the one that already talks to the fork, so start here.
3. **Security.** Localhost only, no auth, like the fork. Say so in the docs.

## Acceptance

- A small client (Python is enough; Elixir via `grpc` is the stretch of the
  stretch) subscribes to `WatchHits` and prints each hit within a second of a
  Surveyor hover.
- Closing the client, or killing `gama serve`, leaves nothing running.
- The service binds only to a loopback address, and refuses otherwise.
- Documented in `docs/reference/`: the service, the messages, how to run it.

## Notes

- This adds the largest dependency in the epic. Treat "decide not to" as a fine
  outcome of the first decision.
- Mirror's AGENTS.md (§4) requires Kevin's approval for any new Hex dependency,
  so an Elixir gRPC client is a decision for that repo.
