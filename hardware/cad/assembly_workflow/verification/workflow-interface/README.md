# Workflow interface verification

31 workflow regression tests and eight PCB freshness tests pass. Real pinned Linux OpenSCAD verification exported the selected handle, reused its identical cache result on a second export, and passed the selected local handle/lid lift check. Export reports now identify the part, cache result and artifacts, and bind recursive source inputs.

The review reproduced and fixed missing export evidence, concurrent report overwrites and status failures during active jobs. Complete cache JSON publishes atomically; reports publish without replacing another owner. Status observes incomplete or runtime-failed jobs without retrying them. Native exit codes are retained. Corrupted cache evidence and changed sources still fail closed.

The full 94-check assembly batch has now also passed under the final runtime. `full-results.json` and `full-selected-manifest.json` bind that actual rerun for signal r89 and the 77-role assembly. The earlier `status.json` is the pre-batch snapshot and remains unchanged. Historical evidence at commit `99c724e9` is retained separately. No physical-fit or fabrication approval is implied.

`review.json` binds the implementation, tests and observed evidence. Root self-review was supplemented by a subagent review; it is not an external audit.
