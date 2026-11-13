# Workflow interface verification

31 workflow regression tests and eight PCB freshness tests pass. Real pinned Linux OpenSCAD verification exported the selected handle, reused its identical cache result on a second export, and passed the selected local handle/lid lift check. Export reports now identify the part, cache result and artifacts, and bind recursive source inputs.

The review reproduced and fixed missing export evidence, concurrent report overwrites and status failures during active jobs. Complete cache JSON publishes atomically; reports publish without replacing another owner. Status observes incomplete or runtime-failed jobs without retrying them. Native exit codes are retained. Corrupted cache evidence and changed sources still fail closed.

The original full 94-check assembly batch is retained at commit `99c724e9` and in `../handle-r2/` plus `../../pcb_updates/r89/`. It is not represented as a new-runtime pass. These interface fixes invalidate runtime-dependent keys; the new native smoke covers export, cache reuse and one real clearance, while `status.json` records the remaining pending checks. No physical-fit or fabrication approval is implied.

`review.json` binds the implementation, tests and observed evidence. Root self-review was supplemented by a subagent review; it is not an external audit.
