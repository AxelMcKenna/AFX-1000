# FI01 — actual enlarged base with underside fan-tray prototype

This new mechanical candidate combines sealed **CP01** and **FA01** without changing either parent. It integrates the complete actual base, holes, four thermal lands, ten supports, matched nominal TIM/shims, return/positive hardware, plastic carrier, controls, ports, PCBs and accepted wire pair. The current board sources remain **P03db83 / E28fed45opens / E19central3b2a**. Later R1, Seed, PB/J8 and FV01supply changes are not adopted.

The assembly review is `generated/FI01-whole-unit-component-review.3mf`: sixteen separately named source families and **776,586 triangles**, with every source coordinate and face preserved. Retained-group mesh caveats remain explicit; no fused whole-unit mesh is promoted as a manufactured part. Exact nominal STEP parts are supplied for the **960-pin base**, unchanged local manufacturing foot, one tray, two guards and four spacers. Every STEP roundtrip is valid; material, strength, factory tolerances and fabrication release are unapproved.

## Honest native result and recovery

All17 actual interface preflight records pass. The complete162-record attempt produced **161 clear results and one container exit137** (`ps_hardware_other_components_collision`), with no log or STL. Its exact unchanged single-case retry also exited137. These attempts remain rejected/incomplete; they are not relabeled as native passes or physical collisions. Read-only daemon observations show8,321,515,520bytes/10CPU/cgroup2 and no identifiable retained pinned-image OOMevent. That does not prove or exclude a memory cause.

The original problematic expression is a union of ten hardware-versus-obstacle intersections. The **exact source-derived ten hardware positions ×six original obstacle families** were evaluated separately: all60 intersections are empty. All ten index-specific hardware witnesses also pass, including their actual XYZ bounds. This establishes that one original clearance condition by distributivity while preserving every module, clearance and own-pot exclusion. `generated/effective-coverage.json` therefore records **all162 modeled geometry conditions established**, with `original_union_native_execution_completed=false`. The exact branch, complete pair set and evidence bindings are in `generated/hardware-split-plan-v2.json` and `generated/hardware-split-v2/verification.json`. The earlier selector-binding warning is also retained as a rejected helper attempt.

The direct matrix includes15 strict closed/oriented/nondegenerate part outputs,99 empty-condition requirements,31 positive/witness controls and17 review outputs. One of the99 empty requirements uses the complete60-pair recovery described above. The other161 direct records remain unchanged. No further unit-wide native run was substituted for those results.

## Actual construction and source identities

| Interface | Current candidate |
|---|---|
| Base | 334×188.4×6.2/R7, upperZ0, lower−6.2; all real attachment/countersink/contact geometry retained |
| Pins | Exactly77 **whole** source pins removed;960 remain; no partial remnants; volume reduction8316mm³ |
| Feet | Original four XYaxes retained, actual feet and bumpers translated−8mm |
| Foot stack | 6.2plate +2trayflange +6spacer; **Accu SPK-M3-20-A2**, nominal5.8mm engagement |
| Thread receiving abstraction | Actual nominal overlapZ−20..−14.2, with20nm tip/mouth guards; manufacturing foot keeps2.5mm blind tap pilot and original M3thread callout |
| Tray | 334×188.4,1.5deck atZ−26.2..−24.7,2mm perimeter walls, foot columns/flanges, rear266×14outlet |
| Fan receiving frames | Centres(80,165.5)/(254,165.5), maximum40.5×40.5×12.5, bottom−24.7/top−12.2; nominal6mm outlet plenum |
| Guards | Two44mm nominal squares,1mm thick,37perforations plus four mount bores each |
| Fan fastening | Eight **unselected** M3pan20/washer/nut receiving gauges; nominal tip−7.7 leaves1.5mm to base underside; no tolerance guarantee |
| Nominal height | Bumper bottom−36.8, PS01knob top67.2 →104mm overall; compression/stack tolerance/stability unqualified |

The foot screw is source-backed by [Accu's M3×20 specification](https://www.accu.co.uk/pozi-countersunk-screws/9528-SPK-M3-20-A2):20mm listed length, headØ5.6 +0/−0.3, listed head length1.65 and90° head. Listed length/head height are not incoming lot maxima or approved thread/preload limits. Countersunk length includes the head; the fan's pan-screw20mm receiving length is measured **under** its head. They are different stack conventions.

FA01's official Noctua drawing/CAD source hashes and dimensional discrepancy remain bound in `parent_evidence/forced_air_prototype/fan-source.json`; vendor files remain external. The maximum frame is a factual dimensional **receiving gauge**, not vendor blade geometry or a CFD model. FA01's shared floating bolt-axis construction is unchanged:0.30fan registration +0.15half-pitch +0.10tray location =0.55each-axis relative requirement, placing the same straight bolt at the midpoint gives±0.275relative to either receiving hole. All original swept/floating contracts were renewed. Their registration/rotation, bearing area, fastening torque and manufacturing applicability remain unaccepted.

Fifteen actual metal through-bores/countersinks, the nine lower case bolt/nut interfaces, four thermal contacts, original live-node isolation and P03supports are preserved. P03nominal bottom6.5 still matches6.3support +0.2selected shim and5.28land +1.22compressed TIM. No whole6.3..6.7range compression guarantee is implied. The fan tray's global `$fn96` is isolated in a private module, preserving the original control/base tessellation scope. Independent polygon-volume calculations confirm the actual tray/guard/spacer profiles; their small numeric serialization comparisons are not physical manufacturing limits.

## Correlated contacts and preserved failures

The first raw17-case preflight rejected only nominal fan-hardware bearing contact:11,636 triangles, all planar at **Z−27.7 /−26.7 /−26.2 /−12.2**, zero nonplanar triangles and approximately6.02e−12mm³ signed-interference residue. It remains under `history/raw-nominal-mating-preflight/` with exact input reconstruction and the plane audit.

Only those four nominal bearing planes receive a **test-only±20nm slab exclusion withinR3.71 of each of the eight nominal fan-bolt axes** (max washer radius3.7). Actual parts, all other material comparisons and every swept/floating-axis contract are unchanged. This is nominal correlated contact, not a factory/Z-tolerance approval. The existing metal/carrier, nut, foot/spacer and PCB seat guards remain separately named and bounded; no blanket board or hardware exclusions were added.

The new actual-part checks cover cut base versus tray/fan stress/swept fasteners, M3×20versus tray/spacers/actual feet, lowered feet versus tray/spacers, all added parts versus current case/controls/electronics/power/wires, and positive/void witnesses for retained/removed pins and the real5.8mm thread region. Existing external0.25mm P03/E28 clearance, source thickness ranges/extra±0.2Z, all source/receiver minimum bores, H9, TC02 and J13/J14/J15contracts remain in the renewed matrix.

## Thermal, electrical and physical holds

**This is not a cooling pass.** CH20's projection of all35.4315W into a base model is not an actual internal-air or package-path solution. The present designed flow path is beneath the base, with its outlet also beneath the base. There is no designed forced-air path through the metal plate and retained plastic floor to the Seed, pot bodies or other internal heat sources. No metal-wall/lid heat credit applies to this plastic case. A separate internal inlet/exhaust design and actual source-coupling model remain work.

Removing77pins also removes11088mm² of nominal pin lateral area; installed flow, pressure loss, leakage, guard restriction, contact conduction, device temperatures and noise require new modeling and measurements. Source fan loads/startup/stall/fault/tach/control, wiring/feedthroughs and protection are unimplemented. FV01's separate5Vsupply proposal is not adopted. The provisional0.11A/1.32W at12V is not a verified maximum or a closed supply ledger.

Nominal underdeck/table gap10.6mm does not mean all hardware has that gap: guard/table gap is9.1 and lowest fan-head/table gap6.1 before bumper/stack variation. Foot compression, stability, drop/vibration strength, insulating TIM pressure/creep, electrical isolation and full harness/process qualification remain open. The current PTV09pot family's+50°C limitation also remains until a separately qualified higher-temperature alternative is adopted. All physical, thermal, electrical-unit, structural, full-wiring and fabrication-release flags are false.

## Read-only review and safe replay

```sh
python3 -S -m hardware.cad.a12.thermal.enlarged_base_forced_air.audit
python3 -S -m unittest hardware.cad.a12.thermal.enlarged_base_forced_air.test_review
```

Capture/part/assembly producers refuse sealed destinations; no live recapture is presented as replay. Captured subset replay includes the private fan library and validates the same pinned runner seal. Use new, nonexistent model/output directories **inside the repository**, outside this sealed packet:

```sh
python3 -S -m hardware.cad.a12.thermal.enlarged_base_forced_air.replay \
  --openscad hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py \
  --rebind-root hardware/cad/a12/thermal/fi01-new-model \
  --outdir hardware/cad/a12/thermal/fi01-new-output \
  --cases fi_actual_base_tray_collision fi_long_foot_screw_positive_control fa_tray_positive_control
```

The resource-terminated union is deliberately refused by this subset entry. Its exact captured60pairs+10controls can be replayed with `split_hardware_v2` into a fresh repo directory; do not run `--capture-plan` on sealed evidence.

Compiled API: `generated/context-derived.scad`, globals from `generated/config.json`; suppress the inherited case selectors with`"cp_only"` and `fi_case`/`fi_fa_case` with`"fi_only"`. Existing `ui_* /ei_* /eb_* /ps_* /cp_*` remain; new `fi_tray()`, `fi_guards()`, `fi_spacers()`, `fi_fans()` and `fi_fan_fasteners()` preserve source geometry. `generated/parts.scad` now contains the actual960-pin/8mm-lowered-foot variant. This is a new conditional mechanical snapshot, not an approval to build or energize the unit.
