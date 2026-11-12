# Installation workflow adapter

This adapter exports frozen installation geometry for the unified assembly workflow. It does not change the enclosure, wires, connectors or electrical topology. Load `registry.json`, resolve its paths against the repository root, verify its hashes, and invoke the zero-argument module named by each component. `parts.scad` contains direct aliases only, with no top-level solids, transforms or parameter overrides.

The eight roles are the r9 replacement shell, complete cooling structure, fan receiving bodies, internal fan harness, external fan harness, loose tie path, tie-head receiving boxes, and six panel mating reservations. Render the shell in place of the old baseline shell. The cooling structure already contains the r8 support brackets and replacement fasteners: do not add them a second time. Internal and external fan routes must remain separate check targets because the combined operation previously exceeded the bounded native runtime.

All coordinates are installed housing millimetres. The adapter takes no geometric parameters. Change requests must update an owned source revision and its contract before the registry is regenerated; editing an adapter wrapper to translate or trim a part is rejected by `verify.py`. Caller tessellation settings belong in the unified runner's cache key. Upstream explicit facet choices remain in force.

Intentional-contact entries are **descriptions, not permission to skip an entire collision pair**. The r8 plate seating mask is restricted to the exact 0.02 mm slabs specified in the registry and original source. The historical pod/lid contact was zero-volume coincidence; a positive-volume overlap requires new evidence. Fan wires may enter only their own F_J202/F_J203 connector allocations. The root workflow must map those references to its baseline parts and preserve other component checks.

The panel mates are receiving limits with a top at Z26.44 and latches facing negative Y. Their fully seated stack, positive polarization/retention and above-housing wire exits remain unresolved. The tie-head boxes are project limits; the loose strap is not the final tightened shape. These distinctions are recorded as component uncertainty and parameter contracts.

The r11 anode and ground graphs are exported as metadata only: 60 junctions and129 wires, no physical routes. They must not silently become rendered wires or completed harness coverage. A later proposed switch-terminal daisy chain has not been implemented.

Validation:

```sh
python3 hardware/cad/two_board_installation_06/workflow_adapter/build.py
python3 hardware/cad/two_board_installation_06/workflow_adapter/verify.py
```

`compile-r1/result.json` records one pinned Linux CSG compilation of all eight aliases at caller `$fn=64`, with no warnings, source drift or Mac CAD launch. This validates module resolution, not mesh clearance or physical fit. `verification.json` adds direct-alias and registry mutation checks. Root integration owns the unified cache, collision matrix, final assembly and report.

### PCB mechanical freshness bridge

Run `pcb_freshness.py` with `--power` and `--signal` paths selected by the central
assembly manifest, `--output` for a new JSON report, and optionally `--repo-root`.
Paths are relative to that repository; no worktree location is embedded. The
checked-in `pcb-freshness.json` records TBP71 power and sensor native-r7 against
the original PCB inputs whose hashes are pinned by TBH01 `capture.json`.

The host-only bridge uses the repository S-expression parser and
`assembly_layout.outline`. Both boards must have zero differences to return 0.
Missing or unsupported geometry fails closed. It checks footprint presence,
XY/rotation/side, library identity, all non-property physical footprint fields
(including courtyards, fabrication graphics, 3D model declarations, pad and drill
geometry), property values, mounting holes, outline and nominal thickness.
Only UUIDs, net assignments, pin electrical labels and schematic paths are
ignored inside physical records. Conservative ordering/text/graphics differences
may require review; no part-value change is silently accepted. Tracks, zones and
vias are outside this mechanical comparison.

`source_sha256` binds both selected PCBs, the original PCBs, capture, bridge and
parser/outline implementation. `freshness_key` hashes that complete map. Consumers
must rehash those files before reusing a report and run the bridge again if any
hash or selected path changes. A passing report preserves the *existing generic
receiving envelopes*, not exact supplier STEP bodies or approved part heights.
External 3D model files are not evaluated or certified by this bridge. Existing
height assumptions remain explicitly reported even when geometry is fresh.

`test_pcb_freshness.py` exercises the real captured power PCB: moved footprint,
side change, value change, drill change, courtyard change, translated board
outline and deleted footprint all reject; unchanged input passes.
