# EB01 — enlarged base and retained carrier

This is a separate, reviewable **334 ×188.4 ×6.2 mm/R7** metal-base candidate for the enlarged plastic case. It covers the front strip missing from EI02's old334×157 base. The source boards, controls and accepted input pair remain in their EI02 poses. EI02, H20/CH20/IH20, PS01 and FA01 are unchanged; neither the proposed metal walls/lid nor the fan tray is adopted here.

`generated/AFX-EB01-BASE.step` and `generated/AFX-EB01-FOOT.step` are valid independent exact BREP parts. The complete review assembly is **`generated/EB01-whole-unit-component-review.3mf`**, with ten separately named objects and every source triangle preserved in its actual global pose. `generated/assembly-manifest.json` maps all scene families and checks exact coordinate/triangle roundtrip. The annotated drawing is `generated/EB01-drawing.svg` / `.png`.

The final42-case native record contains seven strict nonempty, closed oriented production/interface outputs,23 empty intersections, seven deliberate positive controls and five explicitly review-only retained groups. Every positive native output reports `NoError`; no warning is accepted. Retained electronics/control/wire/power groups represent assemblies and dimensional reserves, and their mesh caveats are recorded; they are not individual fabrication parts. All physical, thermal, material, thread-strength and release flags remain false.

## Actual construction

| Item | Source-bound geometry / hardware |
|---|---|
| Plate | UpperplaneZ0, bottom−6.2; certified6061-T6/T651 requirement, not supplied material |
| Pins | Exactly1,037 integral3×3×12 pins, pitch7/border12; unchanged H20 proposed count |
| Lower attachment | Nine axes: X8/167/326 at Y8/149/180.4; actualØ3.4 bores through metal and plastic, captured nut pockets/slots atZ5 |
| Lower screws/nuts | Accu **SPK-M3-16-A2**, Würth **03223/DIN934 M3**; undersideØ6.6/90° CSK1.6 deep |
| Feet | Four OD18×19 machined feet at(20,20),(314,20),(20,168.4),(314,168.4); full20mm edge offsets |
| Foot retaining screws | Actual **SPK-M3-12-A2** envelopes, top-faceØ6.6/90° CSK1.6 deep; these screws were omitted from the old review assembly |
| Foot threads | M3×0.5, ≥10mm usable requirement, Ø2.5 blind tap pilot13 deep; foot bottom remains6mm below drill tip |
| Bumpers | Retained **3M SJ5312/7000001166**, nominalØ12.7/H3.6; tolerance/compression/adhesive/load acceptance still open |
| Thermal interfaces | Four original isolated TIM shapes and four lands atZ5.28, including the notched U13 land; original XY preserved |
| P03 supports | All ten original OD6 supports atZ6.3, original M1.6 pilot/thread callout, actualØ6.8 carrier windows |
| Return supports | Original(166,113)/(166,133.125), lowerØ2.4/4.8CSK holes, pin exclusions andØ3.5 carrier windows retained |

The plastic carrier remains structurally continuous except the original local thermal/support windows, nine lower clearance bores, nut pockets and inward slots. There is no unsupported enlarged front floor. Its full actual part is `generated/carrier_geometry.stl`; its mesh is closed and oriented. The new three pocket/bolt interfaces are also witnessed by a deliberately unbored solid that produces112.787mm³ of interference. No neighboring parts were resized to obtain clearance.

Supplier pages: [Accu M3×12](https://www.accu.co.uk/pozi-countersunk-screws/9524-SPK-M3-12-A2), [Accu M3×16](https://www.accu.co.uk/pozi-countersunk-screws/9526-SPK-M3-16-A2), [Würth03223](https://eshop.wuerth.com.mt/hexagon-nut-39). Accu specifies headOD5.6 +0/−0.3 and lists1.65 head length; the listed head length is not an independently provided maximum-tolerance guarantee. Würth lists5.5AF and2.4H, not incoming lot maxima. These remain conservative envelope **requirements**, with supplier/lot acceptance unapproved. The full stated head envelope is retained as a0.35 rim plus1.3 cone; Ø6 countersinks would fail the preserved2.32889mm³ witness. Do not silently substitute ISO4032 for the selected DIN934 nut.

## Datums, mating and exclusions

The EB01 nominal interface matches EI02 **P03 bottomZ6.5**: metal support6.3 +selected0.2 shim =6.5; land5.28 +compressed TIM1.22 =6.5. The exact original source modules have defaults `thermal_shims(height=.2)` and `thermal_pads(board_z=6.5)`. Four nominal1.524mm TIM sheets compressed to1.22 correspond to19.9475% compression, near the provisional20% target. `interface-stack-review.json` distinguishes this nominal construction from the6.3..6.7 board-height allocation. No fixed shim/TIM stack has been proved over that whole range. Incoming measured pad thickness, all-four-land matching, shim selection/steps, post/land variation, compression pressure, package/PCB flatness and isolation require an actual assembly process and measurements.

Only exact planar bearing contacts are removed from Boolean tests: metal/carrierZ0, foot/plateZ−6.2, nut pocket floorZ5 and nominal interface/PCB planeZ6.5 use a **0.00002mm guard**. There is no blanket own-PCB or0.2mm penetration exclusion. Foot thread engagement is abstracted by a3.02mm major-diameter clearance **only inside the declared engaged thread region** for the assembly fit; the manufacturing foot STEP retains the2.5mm pilot. No helical thread fit is claimed.

Nominal lower screw tipZ9.8 extends2.4mm beyond the listed nut topZ7.4; actual length/runout/seat tolerances remain unknown. M3×12 foot engagement is **5.8mm**, not the10mm of available thread. The retained M1.6×4 board screw has2.2mm nominal engagement without a washer; PCB1.76+shim0.4 leaves1.84mm before actual screw tolerance/runout/washer. These calculations are not pull-out or torque approvals. Upper lid hardware remains unselected. Nine-way hole/pocket registration, nut insertion/access, preload, anodize contact surfaces, print/process accuracy and minimum boss wall/slot strength remain open; nominal concentric geometry is not a tolerance-stack guarantee.

The inherited quiet-ground policy is unchanged: CHASSIS remains electrically separate. No anodize or solder-mask insulation credit is taken. Live P12/RAW_N17 contacts require the selected insulating TIM. The original four-land kit does **not** implement the later separate U102/U10 land proposals; their actual paths and whole-unit thermal integration remain work.

## Checks and limits

The new metal/feet/lower hardware are checked against actual EI02 native-bore PCBs, both-face components, inlet/rear bodies, controls/lid, return/positive hardware, H9/TC02 and accepted full wire/joint paths. Metal and lower hardware also retain P03/E28 **0.25mm component-clearance** tests with the existing source thickness envelope and extra±0.2mm board-Z range. TIM/shim seating and their component check are explicitly **nominal6.5**; no whole-range compression qualification is inferred. The accepted wire endpoints remain fed E28groundY126.5/J13, and E28's45 electrical opens remain. J14/J15 complete outgoing wiring, loose Trill leads, later J8/Seed/control replacements and later P9 sources are absent.

The whole-unit fused binarySTL reports `NoError` but fails the independent coordinate/topology gate; OFF and native3MF retain indexed connectivity yet also collapse rounded-coordinate triangles. All failed outputs and exact original commands/contexts remain in `history/`. No faces were repaired, deleted or decimated. The final component3MF preserves each source face and labels retained-group caveats, rather than treating the entire instrument as one fabricated solid.

The actual native metal volume is504,888.0735mm³; exact BREP504,891.9880mm³ differs by0.0007753%, reflecting curved tessellation. The typical2700kg/m³ material assumption gives roughly1.363kg for the base alone, not a measured mass. Four feet add roughly0.0515kg before screws/bumpers. Support/foot/bumper strength and full instrument center of mass require review. Nominal pin-to-table clearance10.6mm becomes10.1mm at the listed bumper-height lower allocation **before** compression, deformation or unevenness; no installed airflow coefficient is guaranteed.

H20's1,037 pins and foot axes match, but this actual part includes fifteen through-bores/countersinks, blind support pilots, notched thermal lands and local supports. Their surface/volume/material/contact effects are not present in an ideal rectangular-plate model. No H20/CH20/IH20 numerical result or heat rejection is inherited. The provisional whole-unit heat/cooling gap remains open.

## Replay

```sh
python3 -m hardware.cad.a12.thermal.enlarged_base.stage
python3 -m hardware.cad.a12.thermal.enlarged_base.verify --openscad /path/to/OpenSCAD
python -m hardware.cad.a12.thermal.enlarged_base.cad     # CadQuery environment
python -m hardware.cad.a12.thermal.enlarged_base.assembly
python3 -m hardware.cad.a12.thermal.enlarged_base.audit
python3 -S -m unittest hardware.cad.a12.thermal.enlarged_base.test_review
```

The sealed snapshot replays from its captured original and derived contexts. `generated/parts.scad` has no top-level output: include it for `eb_part_metal_base()`, `eb_part_feet()`, `eb_part_pads(board_z)`, `eb_part_shims(height)`, `eb_part_floor_cut()` and pocket/slot modules. These are an actual native-checked part API; they are not a fabrication release.
