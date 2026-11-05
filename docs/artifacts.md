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

## Local cleanup

Python `__pycache__/` directories, `.ruff_cache/` and `.pytest_cache/` are disposable and ignored. Remove them when no checks are running; Python and the check tools recreate them as needed. The `.venv/` environment can be recreated with `uv sync --locked`.

Review `git status --short` before cleanup. Untracked hardware scripts, staging candidates and test files may be active work. Hardware `generated/`, `validation/` and fabrication `staging/` directories contain retained review evidence, including source snapshots with recorded hashes; do not treat them as caches or bulk-format their contents.

Avoid blanket `git clean -fdx`: ignored `build/artifacts/` also holds local-only releases and research output. Check the release catalog and the owning research notes before removing build artifacts. The [audio-output pause](reviews/storage-cleanup-20261030.md) must remain in place until its documented retention requirements are met.
