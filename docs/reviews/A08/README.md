# A08 mechanical review

The print package preserves the A08 meshes, quantity-correct 3MF inventory and validation records. Editable sources are in `hardware/cad/a08/`. Physical fit remains unverified.

Archive SHA-256: `e3bdaa783c158dc17b5027ae2466ceb275ba07547d6f86f80e67713faf1be482`.

The newer standalone A11 housing, E25 disconnect-board placement and source wiring are merged into `main`, with their [review package](../standalone-E25-A11/). The original standalone development branch remains preserved. The complete standalone unit is not build-ready.

The archive is stored locally at `build/artifacts/releases/RMX-A08-print-pack.zip`. From the repository root, restore the exact snapshot from Git history with:

```sh
uv run --locked python tools/artifacts/restore.py --name RMX-A08-print-pack.zip
```

See the [artifact catalog](../../../hardware/releases/README.md) for recovery details.
