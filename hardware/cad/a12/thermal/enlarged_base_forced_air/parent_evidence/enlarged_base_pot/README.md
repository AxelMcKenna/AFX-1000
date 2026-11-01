# CP01 — enlarged base with revised pot/knob stack

This separate candidate combines sealed **EB01** with sealed **PS01**. All122 renewed conditional native records pass:12 strict closed/oriented/nondegenerate part outputs,73 empty intersections,23 positive/witness controls and14 explicitly review-only outputs. Neither parent was edited. The complete eleven-object assembly is `generated/CP01-whole-unit-component-review.3mf`; every719,812 source triangle and coordinate survives exact roundtrip. It is a component review, not one fabricated whole-unit solid.

The only physical-layout changes from EB01 are PS01's ten16×16 pot-body classes atZ27.5..43.59998, knob bases49.2/grub axis3, and ten panel boresØ9.5. The four knob part classes and all XY positions remain unchanged. The new physical source remains a proposed **PTV09A-6 family/20mm shaft**, with exact suffix/resistance/taper/hardware and support/anti-rotation unselected. All PS01 receiving allocations and the+50°C pot operating limit remain unqualified; no thermal result is inherited.

The STEP base/foot parts in `parts/` are byte-identical to EB01. The manufacturing foot still has its original2.5mm blind tap pilot. A separate correction confines the **assembly-only**3.02mm thread-clearance abstraction to nominal M3×12 screw overlapZ−12..−6.2, plus20nm tip/mouth guards. EB01's old10mm abstraction represented available thread, rather than actual5.8mm engagement. `EB01-erratum.json` records the exact source mismatch without modifying that seal.

## Source audit and precise scope

All440 EB01 and98 PS01 sealed file hashes were checked before consumption. PS01's32 raw records were independently reintegrated. Its old136+45 source/artifact maps omit two declared transitive sources: `trill-derived.scad` and `generated/repaired-components.scad`. CP01 captures the full literal closure of every declared SCAD source, including unused review modules, into140 files. The Trill helper matches the earlier EI01 seal exactly; the repaired-components source has its explicit current hash bound. The original PS01 maps remain unchanged and are honestly labeled incomplete in `parent-audit.json`.

The native renewal includes:

- All42 EB01 base/feet/bolts/TIM/shim/control/wire and positive-control records, with the corrected foot receiving interval.
- All44 nonfused EI02 records: actual PCB/body/case/control/power/wire/joint fit, source/receiver minimum bores, all J13/J14/J15 service and tail contracts, H9, TC02, rear interfaces, P03/E28 external0.25mm clearance with the source board-thickness range and extra±0.2Z, and all nine witnesses.
- All32 PS01 records: body/environments, other mechanisms, knobs, receiving hardware/shaft extrema, ten panel bores with independent±0.1XY plus0.005 radial provision and+20% registration sensitivity, axial engagement checks and the old failed-stack/bore witnesses.
- Four explicit combined contracts: new body and receiver envelopes versus **all** base/feet/foot-screw/lower-bolt/TIM/shim material; complete receiver review geometry; and a nonempty body witness.

Ten old generic pot rows are removed exactly once. Their new bodies are actual `ui_components()` geometry, so the renewed full-scene checks see them. Local PS01 body-versus-other-electronics excludes its own new body class; hardware-versus-other-components excludes only the corresponding own shoulder/body receiving overlap while retaining the other nine bodies. These are named receiving-envelope contracts, not proof of an assembled simultaneous nut/washer/bushing stack. The PS01 source hardware union is deliberately not tested as an independent physical part against its own panel seat. Panel fit is checked by the explicit bushing-registration gauge; all remaining hardware/environment and all four shaft/knob classes are checked. No source envelope is shrunk to pass.

The retained bearing guards remain20nm at their exact planes. P03 nominal bottom6.5 uses support6.3+selected0.2shim and land5.28+1.22compressed TIM. The wider6.3..6.7 range needs measured pad/shim selection and is not a fixed-stack compression pass. No0.2mm body penetration is excluded. Lower screw/nut/foot stack, incoming tolerances, torque/preload/pull-out, insulating TIM and finish remain unaccepted.

P03 remains **db83**, E28 remains **fed/45opens**, E19 remains original central **3b2a**. The accepted ground-wire endpoint remainsY126.5. Later actual R1/Seed/PB02/J8/P9/FA01 source changes, full outgoing J14/J15 wiring, loose Trill/pot wiring and the enlarged metal-wall/forced-air proposals are **not** adopted. The overall modeled vertical reference is nominal−28.8..67.2 (96mm), reflecting the revised0.8mm knob lift, not an approved instrument envelope.

## Preserved failures and independent witnesses

The initial122-case trial had one strict empty failure:530 zero-volume faces at nominal screw-tipZ−12. All other121 records passed. The exact report, source reconstruction and185 files remain under `history/initial-tip-plane/`. The final receiving hole extends only20nm beyond that tip, and all122 cases were renewed. A separate native0.002mm³ annulus witness proves material is restored **below** the actual screw tip; the same radial point is empty **inside** engagement. A malformed first helper command is also retained as a command failure, not physical evidence.

EB01's fused STL/OFF/3MF precision failures remain parent evidence. No fused whole-model part is promoted here, and no surfaces are repaired, deleted or decimated. Component-review mesh caveats for retained controls, wire and power assemblies are recorded per object. The new base/feet/carrier/attachments/interfaces and five new panel/knob outputs pass their strict mesh gate.

## Safe captured replay

**Do not run EB01's old `stage.py` inside its sealed packet.** That operation live-recaptures and overwrites outputs; it is not captured replay. This second EB01 erratum is recorded outside its seal.

CP01 capture is also explicitly separate from replay: `stage.py` refuses any sealed destination or existing capture. Native replay refuses sealed output overwrites and existing receipts. The captured-rebind entry copies only already captured geometry, changes only its absolute context prefix and writes into new scratch directories. It neither imports live geometry nor edits either parent.

Read-only checks:

```sh
python3 -S -m hardware.cad.a12.thermal.enlarged_base_pot.audit
python3 -S -m unittest hardware.cad.a12.thermal.enlarged_base_pot.test_review
```

Captured native replay into **new, nonexistent** scratch paths:

```sh
python3 -S -m hardware.cad.a12.thermal.enlarged_base_pot.replay \
  --openscad /path/to/OpenSCAD \
  --rebind-root /private/tmp/cp01-fresh-model \
  --outdir /private/tmp/cp01-fresh-output
```

The recorded rebind test independently reruns the foot contact and20% panel-registration empties plus a nonempty geometry witness. The complete122-case set is the default when `--cases` is omitted. A subset receipt is explicitly partial.

Compiled module API: include `generated/context-derived.scad`, supply `generated/config.json` fields as OpenSCAD globals, and suppress `part`, `thermal_part`, `positive_part`, `candidate_case`, `trial`, `ui_case`, `eb_case`, `ps_case` and `cp_case` with`"cp_only"`. Existing `ui_*`, `ei_*`, `eb_*`, `ps_*` families remain available; `cp_pot_hardware()` supplies the receiving union. `generated/parts.scad` retains EB01's standalone base API. This packet is reviewable modeled geometry; all physical, thermal, structural, full-wiring, material/process and fabrication-release approvals remain false.
