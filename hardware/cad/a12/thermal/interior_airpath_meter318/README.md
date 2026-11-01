# AP03 — larger base meter with a real rear approach

AP03 is a separate mechanical prototype addressing AP02's rejected 125 mm² base-meter pressure allocation. It moves each rear baffle wall from Y142–144 to **Y137–139**, with its plates, seals, M2 hardware and filled lead-feedthrough receiving composites translated together by −5 mm. Fans, guards, feet, enclosure, floor/wall openings, thermal lands/TIM, PCB/control poses and accepted historical wires remain fixed. The sealed AP02 originals are unchanged; `analysis.json`'s `parent_geometry_unchanged` refers to those originals, not to equality of the two candidate geometries.

The new two **16 × 10 mm, R1** meter apertures occupy Z−22 to −12. Their nominal curved net area is 318.2832 mm² total; actual authored faceted area is **318.2787 mm²**. Plate side/bottom webs are nominally 2.0/2.2 mm, and the aperture top remains 0.37 mm below the allocated R2.73 upper bolt/nut envelope. Native tests confirm that the enlarged opening does not cut the bolt/seal hardware. These webs and dimensions are receiving requirements with no manufacturing/strength approval.

The larger bays/bolt keepouts remove **19 additional whole 3 × 3 × 12 mm pins**, leaving **899**. No partial pin stubs or neighboring part resizing is used. The new base's exact curved STEP is valid, single-solid and independently round-trips; its volume is **474096.622406 mm³**, equal to the AP02 STEP less 19 × 108 mm³. The native faceted part is 474092.678167 mm³; the 3.94424 mm³ difference is inherited profile tessellation, not an accepted production tolerance.

## Evidence and review artifacts

- `generated/AP03-layout.png` / `.svg`: source-derived dimensioned plan, pin removals and meter/approach section.
- `generated/AP03-BASE.step`: actual valid curved base part; `base-BREP-verification.json` binds the parent, independent mass balance and round-trip. Its original generation source is retained in `base-producer-original.json`; the current producer merely defers its optional CadQuery import until after its existing-output guard. No CAD/numerical regeneration is claimed for that guard-only change.
- `generated/current-native/verification.json`: **32/32 native cases pass**—six strict part/profile outputs, 18 exact-empty collision/void checks, five actual 0.008 mm³ controls and three positive diagnostic witnesses. Checks cover actual rear meter/bolt seal clearance, pressure-boundary coverage, full lower approach core, fan/baffle/pin/plate interference, retained feet/spacer relationships and the captured case/electronics/pots/other-controls/power/wire obstacle families. The source hashes were unchanged during the run.
- `generated/mating-seated/verification.json`: **22/22 renewed supplemental interface cases pass**, including all eight deliberate 20 µm penetration controls using the same numerical guards, plus three surviving radial/axial counterexamples.
- `generated/AP03-complete-modeled-component-review.3mf`: **21 objects / 826258 triangles** with exact coordinate/order round-trip and zero deleted/repaired/reoriented/decimated faces. Five changed families are fresh native exports; 16 explicitly unchanged families reuse exact sealed AP02 meshes. `assembly-manifest.json` binds each original proof, source mesh, actual topology statistics and local copy. Joined reserve/receiving meshes remain review-only; this assembly is not a single manufacturable part or complete loose-wire model.

Strict Boolean part/control meshes require `NoError`, positive volume, closed oriented boundary and no degenerate triangles. Only the two named pure profile gauges use a separate primitive contract, with independently calculated exact polygon volume/bounds and strict topology. A missing solid, forged empty collision row, absent control or omitted assembly family cannot pass the portable verifier.

## Continuous approach bound and pressure limits

The nominal wall-to-fan-back gap grows from AP02's **1.25 mm to 6.25 mm**. The declared −0.30 mm fan-Y receiving registration leaves **5.95 mm**. This is a geometric requirement/sensitivity, not a supplier assembled-position guarantee.

`channel_budget.py` independently contracts the actual source-defined hardware dimensions and derives a conservative area lower bound at **every height Z−22..−6.7**, rather than selecting a sampled minimum. Starting with a 40 mm wide strip, it subtracts the full projected XY bounding rectangle of every M2 nut and shank; it also subtracts the entire right feedthrough rectangle. Those rectangles are extended over the complete height and their overlaps are deliberately double-subtracted, making the bound conservative. The left feedthrough lies outside its fan-back strip.

| Approach scenario | Left bound | Right bound |
| --- | ---: | ---: |
| Nominal 6.25 mm gap | 220.0333 mm² | 216.4333 mm² |
| −0.30 mm fan-Y registration | 208.0333 mm² | **204.4333 mm²** |
| Additional +0.20 mm wall / ±0.20 mm component receiving sensitivity | 189.6916 mm² | **183.2916 mm²** |

The extra 0.20 mm scenario is a proposed receiving sensitivity, not a manufacturer tolerance. A separate native Boolean proves the entire 31 × 5.93 mm lower leg (183.83 mm²) clear of actual parts over Z−22..−12.2, with a declared 10 µm geometric reservation inside each Y boundary. Its 0.008 mm³ positive control survives; restoring the old wall creates a 1215.2000 mm³ obstruction. The right feedthrough's actual intrusion is preserved as a separate strict positive witness, not ignored or described as an empty gap.

At the parent's **5300 rpm / 10 m³/h total / Cd 0.6** planning sensitivity, the common actual 868.2002 mm² guard consumes approximately 4.00654 Pa per fan. The 318.2787 mm² meter consumes **1.71718 Pa at the requested 1.2 m³/h base flow**, leaving **3.32228 Pa for all base approach, turns, pins and outlet losses** from the provisional 9.046 Pa fan head. These are not installed duty-point predictions. Additional approach coefficients K=1/2/4/8 are explicit sensitivities (about 0.375/0.749/1.498/2.997 Pa), with no asserted guaranteed K bound. Equal 0.6 m³/h per branch is a planning case; the actual coupled branch split is unresolved.

The unchanged floor opening still has the C3 projection/turn issue documented by AP02. Leakage, fan system effects, guards, internal air heat transfer and base losses need a coupled model and measurement. Pin removal also changes heat-transfer geometry; no earlier H20/CH20/IH20 thermal result is inherited. Root's latest 37.28570586 W heat provision is not proof of any installed cooling capacity.

## Mating tests and preserved rejected trials

The moved nominal mates were first tested without numerical masks. All 19 raw cases are retained under `generated/mating-raw/`: three nonmate comparisons are empty and eight overlap controls pass, while eight exact-seat comparisons return float32 contact surfaces. `raw-mating-surface-audit.json` classifies **all 19330 triangles**, none outside the declared seat planes/facets, with maximum deviation **15.403535 nm**. The independent portable audit re-reads those actual vertices and bolt domains, so saved certification flags alone cannot establish the result.

`mating_guards.scad` uses the same **20 nm test-only** nominal-seat construction as AP02, translated to the new real interface planes. It applies M3 plane masks only inside R3.71 around eight bolt axes, M2 masks only inside R2.73 around four axes at Y134/139, and named gasket/FIP seat/facet regions. Actual geometry is unchanged. Every deliberate 20 µm overlap is 1000 times larger and uses the same mask; oversized guards or omitted radial/axial controls are rejected. This proves only the correlated nominal contact tests, with no factory, preload, pose or material tolerance approval.

Two early preflights remain explicit rejected evidence. The initial missing `cp_case` configuration emitted hardwarnings and no geometry; it is not a CAD pass. The configured trial's broad approach witness included coplanar boundary residue and failed strict topology. No part was changed to remove that diagnostic: the later exact-interior clear core and separate strict FIP witness establish the relevant scope. `history/reconstruction-map.json` binds the exact historical verifier bytes by the original hashes; every other input resolves to unchanged captured source bytes. Logs and failed meshes remain intact.

## Source scope and safe replay

This is the AP02 historical capture: **P03 db83 / E28 fed with 45 opens / E19 central 3b2a with old R1 / HT01 pots and actual lugs / old accepted wires**. New E28 routing, R1 dc559, PB02-WR01, negative startup and fan-health candidates are not adopted. The next unified scene must capture their actual stable sources and renew the relevant checks; this packet cannot establish latest-unit fit.

Read-only checks from the repository root:

```sh
python3 -S -m hardware.cad.a12.thermal.interior_airpath_meter318.audit
python3 -S -m unittest hardware.cad.a12.thermal.interior_airpath_meter318.test_review
```

`stage.py` is a new live capture, **not captured replay**; it refuses existing outputs. Do not run it in a sealed packet. The native verifier reads the private frozen SCAD context and requires an entirely new output directory; its current source/configuration hashes and the reviewed pinned Linux runner are checked before execution. Absolute captured repository paths are retained, so this is a same-workspace replay rather than an asserted relocated portable build.

```sh
python3 -S -m hardware.cad.a12.thermal.interior_airpath_meter318.verify \
  --openscad /Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py \
  --outdir /Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/ap03-independent-review
```

Fan-frame drawing/STEP applicability, measured matched shims, HT800 compression and custom cutting, contact force/creep/sealing, fan leads and filled feedthrough process, bolt bearing/torque/lifetime, structural webs, electrical power/protection, full wiring and actual airflow/temperature remain unqualified. All physical, thermal, electrical, structural, full-wiring, fabrication and adoption flags remain false.
