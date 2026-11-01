# Controlled CAD restart

Mac CAD runtimes added by the automation are quarantined. No pre-existing user
application or saved design was removed. The remaining12 identified crash
reports were moved into the same reversible quarantine. The47 failed output
logs and their invalid execution report were compressed and verified before
redundant active copies were removed. The
[cleanup record](../qualification_reviews/cleanup_restart_20261030/cleanup.json),
[quarantine receipt](../qualification_reviews/cleanup_restart_20261030/quarantine-completed.json)
and [design preservation check](../qualification_reviews/cleanup_restart_20261030/design-preservation.json)
record the scope. All1,725 files in six checked sealed design/evidence packets
remain unchanged.

`run.py` performs one operation per invocation, using the existing official
Linux/ARM64 OpenSCAD image pinned by digest. It opens no host Mac CAD apps.
The container has no network, read-only source mounts and root filesystem,
no added privileges, a2GB memory limit, two CPUs and a60-second timeout.
Only the new output directory is writable. Fatal exits block subsequent
operations; a timeout removes that exact generated container. There is no
automatic retry loop. Four mocked crash-guard tests pass.

Fresh results:

| Check | Result |
| --- | --- |
| [Boolean runtime probe](results/probe/result.json) | Closed, oriented1.5mm³ solid, expected bounds |
| [NF265 rear-tail clearance](results/NF265_rear_tail_component_collision/result.json) | Empty intersection, no warnings |
| [Matching PCB positive control](results/NF265_PCB_positive_control/result.json) | Closed, oriented0.008mm³ witness within mesh precision |

These checks launch zero Mac CAD applications. They establish only their stated
runtime and geometric scopes. The other enclosure checks, electrical routing,
startup/fault limits and physical qualification remain incomplete.

The isolated KiCad read-only inventory probe also passed:
[`results/kicad-probe/result.json`](results/kicad-probe/result.json). It uses
KiCad 10.0.7 from the official Linux AMD64 image pinned to
`sha256:c8f05703e865a1caa7266851cf4986dd01d5fb1148e4f63382b6a73466ba7e71`
under Docker CPU emulation. This is independent of the ARM64 OpenSCAD image.
The KiCad container has a read-only root and source mount, no network or added
privileges, and private temporary configuration. Only a named candidate output
directory may be writable. Its successful load is a runtime check, not board
qualification. The old Mac KiCad runtime remains quarantined.

From the repository root, use the module entry point with one unused case name:

```sh
.venv/bin/python -m hardware.cad.a12.controlled_restart.run CASE_NAME
```

Existing results cannot be overwritten. Do not run the historical Mac replay
scripts. The [native stop marker](../../../validation/board-qualification/NATIVE-CAD-STOP.json)
still disables those scripts; its isolated-image exception is explicit.
