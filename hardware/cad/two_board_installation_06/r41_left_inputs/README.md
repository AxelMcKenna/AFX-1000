# r41 — NUDGE DOWN and SOURCE INPUT receiving wires

Additive candidate only. Root selection is unchanged by these files. Two formed
panel input edges reserve S01–S11, r22 ground, existing supports and the future
r33 touch-flex sweep. No holder, switch, terminal datum, connector or PCB changes.

| Wire | Native source / net | Destination | Installed centerline |
|---|---|---|---|
| S12 | D_J2001:7 / CONTROL_03 | button_nudge_down:1 | 139.763107 mm |
| S13 | D_J2001:3 / CONTROL_05 | button_source_input:1 | 291.975975 mm |

Both begin with +Z source tangents and end with −Y terminal tangents. R12 is the
minimum centerline radius; all primitive joins are tangent. S12 descends to
Z25.2 then rises westward before the capacitor row and finishes at the unchanged
terminal. S13 first descends 2.5 mm after its source bend, turns west and descends
to Z27.8 before the isolate button, then turns north and descends to Z24.6 for
the west return corridor. Source and net ownership are checked against the
frozen native panel contract/netlist, including all 29 input-terminal datums.
These are installed path lengths, not cut lengths or proven service allowance.

The Alpha5853 maximum insulation radius is 0.5461 mm. The radius 0.6/fn24
receiving hulls contain that wire after a conservative sphere-inscription and
arc-chord bound (0.5856656 mm). The separately executed radius 0.863/fn32 controls
probe guarantees at least 0.2505967 mm beyond the ideal radius 0.6 route:
`0.863*cos(pi/32)^2 - 12*(1-cos(1.5deg)) - 0.6`.
Both sphere sets use rotation [17,23,31]. The verifier reconstructs every executed
hull/sphere line, point, radius, facet count and rotation. No positive volume is
waived. Host wire surface clearance is at least 0.4218006 mm; clearance to other
reserved input-terminal spheres is at least 2.0458879 mm. Independent exact
chord-to-box bounds cover all 2097 retained component allocation boxes, with a
minimum surface gap 0.3532312 mm; these are captured receiving boxes, not STEP
claims or a substitute for root's current PCB population screen.

The final native set uses r9 physical positives/intersections and the exact
unchanged r8 clearance-positive source. The r9 union/S12/S13 have 38474/16334/22140
triangles, zero excluded degenerates and zero bad directed edges. The margin
operand has 53562 triangles, 14 excluded degenerates and zero bad directed edges;
its remaining oriented boundary is closed. All seven final intersection cases
must be EMPTY: selected controls with margin, receiving allocations/supports,
previous and mutual wires, structure, future touch flex with margin, original
unrelieved controls with margin, and display lid/guide with margin. Each job is
pinned Linux OpenSCAD with a 60 s, 2 CPU, 2 GB bound. `verify_native.py` remeasures every
retained STL and binds sources and artifacts; `export_adapter.py` refuses a
failed or stale final set. Nine contract mutations must be rejected.

Rejected evidence is retained, never silently converted to pass:
- r1–r3: nonclosed margin meshes; r1 physical wire union was closed.
- r4: actual capacitor/pot/header allocation intersections 27.153137 mm3 and
  future touch sweep intersection 10.592469 mm3. Other local cases were empty.
- r5: native margin positive closed, but host S12/S13 crossing failed. No old
  successful host report is credited to that route.
- r6: margin mesh had 3 bad directed edges; collision checks did not run.
- r7: isolate mechanism/holder collision: 12.556604 mm3 expanded control and
  6.325510 mm3 actual structure. Receiving/wires/touch/lid were clear.
- r8: margin closed, physical wire union had 10 bad directed edges. r9 changes
  only physical sphere orientation; analytic paths and margin source unchanged.

Self-review corrected a physical sphere bound that had accidentally used the
margin's fn32 instead of physical fn24 during the rejected r7 report. The final
formula uses fn24 and still contains the full maximum insulation radius.
Exploratory search logs are planning only and are not qualification evidence.

Full current assembly screening—including current main fastener stacks and
`main_fastener_receiving_r1`—is still required at root. Terminations, connector
registration, wire/support tolerances, strain relief, retention and lid-opening
slack remain unqualified. These two receiving edges do not complete the harness
or count any touch wires; after root acceptance 13 panel edges would be modeled
and 217 further non-ground segments would remain.
