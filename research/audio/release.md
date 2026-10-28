# Release effect matching

29 October2026. The [first40-program original-reference comparison](measurements/2026-10-29-release-initial-comparison-failed.json) passes the four neutral baselines and fails all36 active Release programs. All original input/receipt/binary/control-readback hashes are checked. The three types are Back Spin, Echo and Vinyl Brake, each at raw lever85/170/255 with a stereo tone, impulses, chirps and deterministic broadband program. Whole/activation/active/return windows use fixed32/32 and the unchanged1% per-channel gate. No alignment/gain is fitted.

These results expose gaps in the existing production approximations. They are development discovery, not prospective qualification. The first comparison attempt was rejected before rendering because original capture had not yet completed its matrix; no partial recording was scored. Original recordings and binaries remain ignored local artifacts.

`tools.rmx_release capture` creates the reference programs with an explicit original Intel host and pinned2.2.0 bundle. `tools.rmx_release compare` validates the saved artifacts and uses the actual Engine fixture `rmx_release_probe`. New destinations are required. The next step is control/clock/playback identification, followed by frozen fresh predictions and independent validation before adoption.
