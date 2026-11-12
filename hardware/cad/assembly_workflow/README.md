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
