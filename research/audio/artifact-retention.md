# Audio research artifact retention

Keep render output temporary. Do not clone whole research trees or retain every intermediate WAV, sanitizer copy, prediction render or build snapshot.

The bounded Noise and drum replay tools use one case at a time, enforce a512MiB temporary-data limit and delete audio before proceeding. Noise retains compressed two-second band/total powers, correlation and small receipts; drums retain whole-WAV hashes and links to qualified prior evidence. The independent Noise auditor works from those retained summaries. These summaries cannot substitute for raw audio in a future waveform/transient investigation; recapture only the needed case.

Use:

- `uv run --locked python -m tools.rmx_noise_stream --help`
- `uv run --locked python -m tools.rmx_drum_replay_stream --help`
- `uv run --locked python -m tools.rmx_noise_power_audit --help`

Keep the local `.rmx-audio-output-paused` marker while using these bounded workflows. It blocks legacy output paths under that checkout; the new runners use automatically cleaned temporary directories. It is a local operational marker, not a tracked project asset.

Published reports retain failed and inconclusive verdicts. Preserve small source manifests and useful numerical diagnostics. Keep one current playable preview and the canonical reference installation. Historical raw-capture paths from before the30 October cleanup are intentionally unavailable; the cleanup archive preserves deduplicated metadata and research sources.
