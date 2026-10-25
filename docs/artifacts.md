# Generated files and review artifacts

| Kind | Location | Git policy |
| --- | --- | --- |
| C++/Python/OpenSCAD sources and editable KiCad designs | `include/`, `src/`, `tools/`, `hardware/` | Track |
| Small generated coordinates, board drawings, exported netlists and verification records | The owning hardware directory's `generated/` or `validation/` | Track for review; regenerate with the documented tool |
| Selected documentation previews | `docs/assets/hardware/` | Track reviewed snapshots; update deliberately |
| Mechanical meshes, DXF exports and render PNGs | `build/artifacts/cad/` | Ignore; regenerate |
| Historical review ZIPs and packaged firmware | `build/artifacts/releases/` | Ignore; retain checksums and recovery information in `hardware/releases/` |
| Large research measurements and experiment output | `build/artifacts/research/` | Ignore; link checksums/summaries from the research note |
| SDKs, compiler output and caches | Existing ignored `build*/` and cache directories | Ignore |

The [release artifact catalog](../hardware/releases/README.md) records exact filenames, sizes and SHA-256 values. Existing bundles, including the A08 and E25/A11 snapshots formerly under `docs/reviews/`, were moved locally without altering their bytes. Previously committed artifacts can be restored from the recorded Git blob with `uv run --locked python tools/artifacts/restore.py`; uncommitted bundles require their retained local copy or a separately published release asset. No release assets were uploaded by this reorganisation.

Future distributable review bundles belong on versioned releases with checksum manifests. The source tree keeps their small manifest and instructions. Moving existing bundles out of the current tree does not rewrite their Git history.

Historical verification JSON and archived ZIP contents retain their original snapshot paths and hashes. Fresh verification tools fingerprint the current layout. Generated evidence describes its recorded check scope; moving a file does not turn an old result into a new validation.
