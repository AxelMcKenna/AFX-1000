# Storage cleanup — 2026-10-30

Disk exhaustion came primarily from retained audio-validation outputs under
`build/artifacts/research` and the temporary
`/private/tmp/rmx-shared-engine-live/build/artifacts/research` copy.

The active drum compatibility writer and its children were stopped. Cleanup
removed 239,909 generated `.wav`, `.wav.gz` and `.bin.gz` files from those two
trees. Canonical `research/audio` source folders, including copies nested in
source snapshots, were excluded. Code, CAD, releases and report metadata were
outside the deletion scope.

The cleanup journal measured 550,215,012,352 bytes of additional volume space
available after deletion. File-size totals are larger because APFS shared
extents must not be counted as independently reclaimed storage.

Raw render references in historical validation reports now require
regeneration. Retained reports do not imply that their generated WAVs remain
available. The file-by-file deletion journal and summary are at
`/private/tmp/rmx-disk-cleanup-20261030-removed.jsonl` and
`/private/tmp/rmx-disk-cleanup-20261030-summary.json`.

Bulk audio output is paused using `.rmx-audio-output-paused` markers in both
workspaces. Shared output-directory, WAV-writing and reference-render entry
points honor the pause before writing or launching render work. Three small
regressions cover paused output, normal output and a symlink into a paused tree.
Streaming comparisons, automatic temporary cleanup and bounded retention must
be implemented before removing the pause. No bulk audio validation was rerun
during cleanup.
