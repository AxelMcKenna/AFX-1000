# Standalone E25 / A11 review snapshot

The archive preserves the verified CAD print packs, native check records, rendered reviews, source patch and per-file SHA-256 manifest from the E25/A11 development milestone. The matching editable design sources are committed in this branch.

Archive SHA-256: `58c7469313def2ab038236de0ecea611d5880b044bcaf8a71d5a81a017325110`.

This is an in-progress standalone design, not a fabrication release. E25 still has 365 open connections; both provisional 5 V harness loss screens fail. Remaining routing, distribution changes, wiring and physical qualification are documented in the archive and `hardware/validation/disconnect-placement.json`.

The archive is stored locally at `build/artifacts/releases/disconnect-placement-E25-A11-review-20261024T234402Z.zip`. From the repository root, restore the exact snapshot from Git history with:

```sh
uv run --locked python tools/artifacts/restore.py --name disconnect-placement-E25-A11-review-20261024T234402Z.zip
```

See the [artifact catalog](../../../hardware/releases/README.md) for recovery details.
