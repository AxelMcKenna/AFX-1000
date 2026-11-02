# Audio research artifact retention

Keep render output temporary. Do not clone whole research trees or retain every intermediate WAV, sanitizer copy, prediction render or build snapshot.

The bounded Noise and drum replay tools use one case at a time, enforce a512MiB temporary-data limit and delete audio before proceeding. Noise retains compressed two-second band/total powers, correlation and small receipts; drums retain whole-WAV hashes and links to qualified prior evidence. The independent Noise auditor works from those retained summaries. These summaries cannot substitute for raw audio in a future waveform/transient investigation; recapture only the needed case.

The modulation runner additionally deletes native audio before rendering ASAN, then deletes ASAN before the Original capture. Its extended comparisons retain only one whole WAV at a time. Read-only internal-buffer diagnostics use short temporary captures and keep numerical errors, correlations and timing fits after deleting their private audio intermediates.

The Sidechain runner keeps one synthetic input and one output WAV at a time, within the same512MiB budget, and checks dry-stem subtraction separately. Retain failed detector hypotheses and inconclusive audio verdicts alongside successful control and delivery checks. Its separate reference-host build changes only an input-duration guard; preserve the old host until the byte-identity bridge is verified.

The [performance-path runner](../../tools/rmx_performance_path.py) pairs each active program with an explicit drum/source control, deletes optimized output before ASAN and deletes ASAN output before the Original render. It retains per-channel reference/error energies for complete, one-second, event and effect-difference windows. The separate [energy auditor](../../tools/rmx_performance_path_audit.py) recomputes those verdicts after cleanup; it does not recreate raw audio. The preservation and wrapper-delivery runners also use serial, automatically cleaned temporary directories. Read-only debugger observations retain bounded control metadata and complete ordinary/observed artifact hashes.

Use:

- `uv run --locked python -m tools.rmx_noise_stream --help`
- `uv run --locked python -m tools.rmx_drum_replay_stream --help`
- `uv run --locked python -m tools.rmx_noise_power_audit --help`
- `uv run --locked python -m tools.rmx_performance_path --help`
- `uv run --locked python -m tools.rmx_performance_path_audit --help`

Keep `.rmx-audio-output-paused` in place while using these bounded workflows. It blocks legacy output paths under that checkout; the new runners use automatically cleaned temporary directories.

Published reports retain failed and inconclusive verdicts. Preserve small source manifests and useful numerical diagnostics. Keep one current playable preview and the canonical reference installation. Historical raw-capture paths from before the30 October cleanup are intentionally unavailable; the cleanup archive preserves deduplicated metadata and research sources.

The [Scene-switch checkpoint](scene-switching.md) retains compressed regression/holdout windows, failed hypotheses, source snapshots, corrected observer interpretation and native diagnostic identity receipts. Original assembly is excluded. Its separate preservation replay checks 180 manual programs, 99 earlier prediction hashes and 18 final optimized/sanitized switch outputs. Source snapshots preserve intermediate hypotheses without keeping their compiled builds.

The [2 November tempo checkpoint](tempo-transitions.md) keeps compressed waveform-window reports, read-only control traces, zero-input geometry predictions, failed source models and a complete-WAV bridge to the final Echo cleanup. Preservation separates unchanged outputs from the seven intentional tempo changes, which require new Original qualification. The rejected Echo time-knob coupling remains a failed hypothesis in provenance.
