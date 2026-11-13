# Unified assembly workflow

This is the entry point for mechanical integration. `current.json` selects the active component registries, current KiCad boards, housing variant and clearance checks. Existing CAD sources remain authoritative; adapters apply their installed transforms once and do not copy or redesign parts.

Use `./hardware/cad/assembly_workflow/run` as the short command (for example, `run status`, `run scene`, or `run check`). The equivalent explicit commands from the repository root are:

```sh
.venv/bin/python -m hardware.cad.assembly_workflow.workflow status
.venv/bin/python -m hardware.cad.assembly_workflow.workflow scene
.venv/bin/python -m hardware.cad.assembly_workflow.workflow scene --reservations --motion
.venv/bin/python -m hardware.cad.assembly_workflow.workflow check
.venv/bin/python -m hardware.cad.assembly_workflow.workflow check --only panel_mates_sensor_harness
```

`scene` writes one assembled SCAD entry point at `generated/assembly.scad`. The default is the one-piece structural assembly. Receiving envelopes and motion sweeps are opt-in, translucent layers. Atomic switch/clip/holder alternatives and split-lid bars are excluded when their composite or one-piece replacement is selected. Main-board allocations omit the seven connector reservations replaced by current panel and sensor mates. Nominal shafts, shims, springs, button mechanisms and touch parts come from existing sources; unresolved exact supplier geometry stays explicitly labeled.

## Setup and daily loop

From the repository root, use `uv sync --locked` to prepare the repository's `.venv`. Native checks also require the Docker engine and the pinned OpenSCAD image named in `hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py`; the runner never pulls a different image automatically. Status and planning do not launch CAD.

1. Run `./hardware/cad/assembly_workflow/run status` to inspect PCB freshness and check states.
2. Edit the owning parametric SCAD source or native KiCad candidate in the task's isolated worktree. Keep supplier assumptions and installed transforms in the component registry.
3. Run `plan --manifest path/to/candidate.json`, then `check --manifest path/to/candidate.json --only affected_check --output path/to/new-evidence.json`.
4. Export selected parts with `export --manifest path/to/candidate.json --only component_id --output path/to/new-export-report.json`. The report identifies the component, cache result, artifact hashes and frozen source inputs; the STL stays in the content-addressed cache.
5. Hand the candidate and evidence to the integration owner. That owner reviews the delta, runs all configured checks, then updates `current.json`. Selection remains explicit.

Each owner uses unique report paths. Complete reports publish without overwriting an existing destination, including a competing writer. Cache JSON publishes atomically. Status labels incomplete and runtime-failed jobs without restarting them; only explicit diagnosis and recovery can clear a stopped job.

The PCB bridge checks mechanical freshness, not electrical correctness. Each PCB handoff must separately include its revision-specific native DRC/ERC, connectivity, return/reference checks and portable verifier bound to the exact board hash. Foreign filled-zone cutbacks require explicit layer/net ownership and a native delta audit; a mechanical pass cannot authorize them. Automatic routing search and electrical verification remain their existing scripts rather than a new CAD system.

## Candidate work and parallel ownership

Each agent uses its existing task branch and isolated worktree. The integration owner alone changes `current.json`; candidate checks never promote a design. Use the same runner directly for a candidate, without Python monkeypatches:

```sh
./hardware/cad/assembly_workflow/run status --manifest path/to/candidate.json
./hardware/cad/assembly_workflow/run scene --manifest path/to/candidate.json --output path/to/candidate-view.scad
./hardware/cad/assembly_workflow/run check --manifest path/to/candidate.json --only check_id --output path/to/new-results.json
```

Manifest paths are relative to the repository root (absolute paths within that worktree also work). Registry and source paths remain repository-relative. Candidate scenes require an explicit output so the selected assembly view is preserved. Check/export evidence must use a new output path; existing evidence is rejected before native work starts. All existing freshness, source-binding, immutable-cache and failure rules apply to candidates too.

Before handing a candidate to integration, retain its manifest, exact source hashes, commands, native results and rejected witnesses. Declare changed PCB identities/nets or geometry roles and the remaining qualification limits. Integration reviews those deltas and runs the candidate checks before selecting it. Identical nets do not make connector ownership interchangeable; extra touch wiring must not be counted as completed panel-inventory edges.

Use `status`/`plan` before native work and `--only` while iterating. The final integration batch covers all selected checks. A runner-code change intentionally invalidates native cache keys; historical results remain evidence for their original runtime, not a new pass. Native PCB zone-fill experiments must retain crashes and must not be automatically retried or treated as successful boards.

## KiCad mechanical freshness

Before scene/export/check work, the bridge compares both selected PCB files against the CAD capture: outlines, thickness, mounting holes, footprint presence/position/side, physical footprint fields, courtyards, pad/drill geometry and part properties. Mechanical changes block stale CAD checks. Pure routing changes can retain the mechanical cache after comparison. Board results are themselves source-bound and cached; the full batch checks the board, manifest and registry snapshot again before reporting success. Supplier heights remain receiving assumptions.

## Incremental checks

`plan` and `status` identify pending, passed and interfering checks. Each check is keyed by its exact operands, recursive SCAD dependencies, runtime/mesh-check code, facet resolution and pinned Linux image. Descriptive metadata changes do not invalidate geometry; changed dependencies invalidate only affected component/check keys. Registry source bindings must match, so a changed component cannot silently inherit stale receiving metadata. Adopting a new candidate means updating its owner registry and evidence first, then selecting it in `current.json`.

A check first proves every operand is nonempty for the same frozen source snapshot. Native jobs read immutable copies of their recursive SCAD sources; manifest and registry hashes are taken from the exact bytes parsed, not from a later reread. It caches native part exports. Closed manifold operands are reused for fast intersections; multi-part assemblies with balanced contact boundaries use their original CAD source instead of importing an unsuitable STL. Open/unbalanced geometry fails. Sources are checked again after rendering and across the complete batch, closing the race between positive operand checks and the intersection.

Cache files are immutable, content-addressed and ignored by Git. Logs, source, mesh hashes and failures are retained in `cache/`. A repeated unchanged check uses the previous result; a confirmed interference remains a failure. Runtime warnings, source drift, incomplete jobs and corrupted artifacts stop execution. Each native job has a 60-second limit and an isolated, named container. No native macOS CAD application is launched.

An interrupted/runtime-failed job can be archived after diagnosis:

```sh
.venv/bin/python -m hardware.cad.assembly_workflow.workflow recover \
  --job component/CONTENT_HASH --reason "Specific cause and correction"
```

Recovery preserves the failed evidence, refuses a live owner/container and does not rerun anything. A later explicit check can create a fresh job. Geometry failures require a design/source correction; they are not recovery targets.

## Current coverage and limits

The initial eleven strict intersection checks cover the corrected sensor cable, conditional panel mates, final control carriers, lid/guide and cooling paths. They replace the repeated hand-written integration wrappers for that scope. They do not certify every possible component pair or replace each part's frozen local seating, insertion, retention and motion evidence. Contact metadata is visible in status and never becomes a blanket collision waiver.

`current.json` lists remaining design gates. The actual magnet/grub-screw geometry, supplier-certified envelopes, complete panel harness, analog/power qualification and physical assembly remain separate work. Passing this workflow is not fabrication approval. The default view is structural, not a claim of complete installed hardware.

## Design decision

Keep OpenSCAD and KiCad and consolidate their interfaces. Migrating CAD kernels would change geometry while solving an orchestration problem. One small Python runner, registries and thin SCAD adapters give a shared assembly, reproducible operands, automatic invalidation and recoverable failures without adding a server or a new CAD system. Binary STL caching is used only for closed manifold operands; original-source checks remain the fallback for contact-rich assemblies.

The earlier r13 ground role added two 12 mm-radius source exits as receiving geometry. Three additional checks cover the current sensor, controls and cooling assemblies (14 configured checks total; 59 roles). These checks validate only the exit pair, excluding its own conditional connector termination, and do not qualify the downstream harness. Native evidence is in `verification/formed-ground-r13/`.

The historical r14 selection replaced the combined r13 exits with the complete19-button left chain plus the right-source exit (61 roles;14 checks). Root screening found three BPM-display collisions in r3; the r4 reroute passes all three current sensor/control/cooling checks. Native evidence and the rejected witness are retained in `verification/left-ground-r14/`. At that checkpoint, the scene/selector branch, supports, slack and terminal qualification remained open.

The r15 ground checkpoint combined both formed branches and one splice (64 roles;14 checks). All three root cross-fit checks pass; `verification/ground-r15/` retains the selected combined registry and evidence. This completes ground routing geometry only, not all panel wires, supports or service qualification. At that checkpoint, the original fixed lever obstructed vertical lid removal; `../two_board_service_10/` records the failed lift path and a verified removable-crossbar candidate.

The earlier signal checkpoint was DAC r26:198 native open connections after32 new joins, with477 unchanged footprint poses. Root-local portable verification checks146 frozen source/evidence files; the PCB mechanical bridge remains fresh. Selected clearance results can therefore be reused. Eight DAC joins and the approved ESS footprint remain open; this is not analog-noise or fabrication qualification. See `verification/signal-r26/`.

The r16 checkpoint installed the conditional splice cage and replacement selector hardware (65 roles; 18 checks). All configured checks pass. See `verification/ground-r16/`; actual retention, strength, tool access and full service motion remain unqualified.

The r18 checkpoint added the keyed R13 guide and replacement selector rear hardware (66 roles; 22 checks). See `verification/ground-r18/`. Separate removable-handle withdrawal/tool-space checks also pass against the current modeled assembly; full service opening remains unqualified.

The current selection has 84 roles and 157 passing clearance checks: signal r131 (164 opens), TBP73 (1936 opens), corrected scene ground r22 and nine receiving panel inputs. `mechanical_capture` selects the cumulative R303/R308/D101 update under `pcb_updates/r125/`. Native screening rejected the earlier S02 control collision and a tight nominal revision before accepting r13 with an expanded control-clearance probe. See `verification/panel-signals-r21-r13/`.

There are 221 further non-ground signal/power segments. The wider main-population screen passes controls and sensor checks, while `verification/coverage-01/` records an unresolved own fan-connector reservation/harness mismatch. The isolated buck and single-row connector candidates remain unselected. Full service, physical receiving, electrical/thermal and fabrication gates remain open.

The selected r24/r25 integration replaces the duplicated fan-bundle reservation and broad touch context box with source-bound detailed geometry. All six fan wire paths and original fan connector body reservations remain. The r24/r25 checkpoint passed39 checks under the direct-manifest workflow; see `verification/fan-touch-r24-r25/`. The selected r26 revision adds the two pocket extensions, exact nominal touch hardware and upper receiving envelope. That mounting checkpoint passed57 checks; three raw seat witnesses remain explicit. See `verification/touch-mount-r26/`; physical mount tolerance, assembly and retention qualification remain open.

The historical r78 signal checkpoint preserves all477 poses and remains mechanically fresh against the r62 capture. All57 selected checks pass for its exact PCB identity; root portable reference/transition verification is retained in `pcb_updates/r78/`. At r78 one modeled DAC connection remained; r82 closed it, while ESS and analog qualification remain open.

The removable-handle integration passed94 checks under its recorded runtime and preserves the latest PCB selection. It removes the fixed-crossbar obstruction for a neutral-lever local lift, without qualifying full wired service or printed threads. See `verification/handle-r2/` for the native preview and evidence. Signal r131 is mechanically fresh and has 164 opens; see `pcb_updates/r131/`.

The subsequent workflow publication/status fixes intentionally invalidated native cache keys. All 94 selected checks have now passed again under that final runtime; see `verification/workflow-interface/full-results.json`. Workflow regression tests, fresh native export/cache smoke evidence and the frozen assembly selection are retained alongside it.

The removable touch-mount nut tool also passes ten process-clearance checks against all 76 external selected roles; see `verification/touch-tool-r30/`. It requires 40 mm underside fixture access and remains a removable process tool. Nut bearing contact, washer registration, torque and physical retention are not qualified.

The selected S04 panel input adds ten checks against all77 prior roles, yielding78roles/104checks; see `verification/panel-signal-r34/`. The separately sourced main-mount hardware study found copper beneath D_H4’s nominal bearing area; selected r107 now clears that copper and enforces native keepouts. For the conditional hardware study, see `verification/main-fasteners-r1/`. The subsequent r2 full-stack integration is selected as conditional nominal geometry; physical receiving remains unqualified.

TAP/AUTO replace both scene-zero holder roles using the verified plastic-only relief; NUDGE UP requires no additional holder change. See `verification/panel-inputs-r37/` and `verification/panel-input-r38/`. The r125 integration passed 145 candidate checks (135 permanent plus ten moved-body diagnostics). The first broad diagnostic exited137 without a geometry result and was replaced by ten checks over exactly the same80 obstacles. D101/A_C105 receiving envelopes have only0.02mm separation; this is nominal noninterference, not manufacturing tolerance proof.

The isolate 0/1 pair passed the full 147-check assembly screen; see `verification/panel-inputs-r39/`. Its eleven external checks use the pair union against all81 prior roles, with a separate mutual check and individual positive meshes.

For additive panel-wire batches, use `python -m hardware.cad.assembly_workflow.stage_panel_inputs --registry REGISTRY --progress LAST_SELECTED_INVENTORY --output NEW_REVIEW_DIRECTORY --prefix REVISION`. It validates inventory/net identities and required roles, preserves every previous check, and generates union/mutual coverage. It rejects component replacements and existing candidate directories, freezes its staging source with the evidence, and never runs CAD or selects a design. Run the normal candidate workflow and review the evidence before selection.

The main-fastener r2 checkpoint replaces22generic heads with sourced nominal complete stacks, retaining the two sensor-owned mounts. All157checks pass, and all22conductive bearing regions clear selected-board copper. Own44seat planes are retained separately, not called empty intersections. See `verification/main-fasteners-r2/` for the conditional budget, section preview and physical qualification limits.
