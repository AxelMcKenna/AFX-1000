# S04 scene-4 input candidate

S04 connects **D_J2002 cavity6**, `/D_CONTROLS/CONTROL_23`, to **scene4 B3F
terminal1**. The source receiving datum is [226.08,48.46,27.04] mm; the frozen
terminal datum is [276.447362,54.077339,31.6] mm. Exact source ownership/net and
receiver are checked against the retained panel native netlist/contract and
r19 inventory. Neither existing ground feeds L01/R01 nor S01–S03 changes.

The source emerges southwest at220° with a circular R12 bend, descends through
a tangent R12 S curve to Z31.2 and uses the rear corridor above the captured
connector bodies. A R14 turn leads toward scene4. Two R12 arcs make the final
0.4 mm rise to its unchanged receiving terminal, ending tangent +Y. Exact
formed centerline length is180.658470 mm; **this is not a cut length** and
excludes preparation, connector internals, solder geometry and service slack.

The selected Alpha5853 wire maxOD1.0922 mm fits the0.6 mm-radius wire model.
Minimum bend radius12 mm exceeds the retained10×OD requirement10.922 mm. All
circular primitives and sampled points reconstruct exactly; tangent joins are
continuous. Analytic selected-wire separation includes both wires' arc chord
errors: minimum modeled surface gap0.417989 mm, nearest ground feedL01. All29
input-terminal reservations remain protected; minimum other-terminal surface
gap6.815082 mm. The expanded fn24 control probe radius0.88 mm covers more than
0.25 mm extra margin after sphere tessellation and chord errors.

## Receiving and assembly limits

The r10 source interface remains the conditional Molex901310128 male,
901420016 female and901192120 terminal selection. Controlled mating stack,
termination/retention, actual solder approach, strain supports and fixed-board
to lid opening allowance remain unqualified. No source-height change, second
wire in a cavity, blanket contact exclusion or altered motion envelope is used.
S04 reserves space around all selected ground branches, S01–S03 and the r33
conditional touch-flex receiving envelope. It requires the explicit r22 ground
variant. Root full-assembly review must precede selection or reducing its227
remaining non-ground panel inventory by this one edge. Extra touch wires are
not part of that inventory.

## Retained rejected evidence

- r1: original23.2 mm corridor produced a non-closed21,008-triangle wire mesh
  (one degenerate triangle, three bad directed edges). Rotating sphere
  tessellation preserved centerlines/radii and produced a closed r2 mesh.
- r2: that low corridor collided35.724194 mm³ with rear output connector
  receiving allocations, including output_ts_r atX192.5–211.5,Y0–28,topZ23.5.
  The source and exact witness remain under `rejected-r2-receiving`/`native`.
- r3: raised corridor cleared receiving geometry and selected wires, but the
  expanded control-motion margin failed by0.004894503 mm³ near the source
  (X225.107–225.700,Y46.246–46.919,Z33.2–34.1415). This was not waived; r4
  changes source emergence/descent and passes the expanded control test.

- r4: all local intersections were empty, but its positive STL had three
  degenerate triangles/three bad directed edges. It is retained as rejected
  evidence. r5 changed only sphere orientation and also failed closed-boundary
  validation (ten degenerate triangles, six bad directed edges).
- r6: the same centerline/radii with fn24 rotated spheres exports a closed
  15,180-triangle boundary (two zero-area triangles excluded, zero bad directed
  edges). The inscribed radius after chord error is at least0.584980 mm, above
  the maximum insulation radius0.5461 mm. The expanded control margin remains
  at least0.260210 mm. Every local clearance is rerun for this exact source.

The host-only corridor search is planning evidence, never native clearance.
`verify_native.py` binds all accepted and rejected native sources/results,
logs and meshes. `test_contract.py` rejects wrong cavity, wrong net, moved
terminal and subminimum bend mutations. No fabrication release is claimed.

Self-review added conservative chord error to mutual and nonlocal self checks,
separated exact arc length from sampled length, and preserved the small failed
control-margin witness instead of accepting a tight nominal route. The frozen
old wire/control/receiving envelopes remain authoritative.

## Final local checkpoint

All five r6 intersections are empty: expanded control motion, receiving/support
geometry, selected wires, housing/structure and future touch flex. The positive
operand has a closed boundary as described above. The source-bound adapter is
`../workflow_adapter/panel-input-r34-registry.json`, exporting the zero-argument
`panel_signal_r34_scene4()` receiving role. It does not change `current.json`.

```
.venv/bin/python -m hardware.cad.two_board_installation_06.r34_panel_inputs.verify
.venv/bin/python -m hardware.cad.two_board_installation_06.r34_panel_inputs.test_contract
.venv/bin/python -m hardware.cad.two_board_installation_06.r34_panel_inputs.verify_native
.venv/bin/python -m hardware.cad.two_board_installation_06.r34_panel_inputs.export_adapter
```
