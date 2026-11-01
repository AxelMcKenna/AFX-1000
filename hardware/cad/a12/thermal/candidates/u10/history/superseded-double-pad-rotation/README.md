# U10 — LT3090 thermal-path feasibility

**A front-side U10 relocation provides a real thermal-path candidate; it is not qualified or electrically complete.** The saved candidate has zero ERC/parity/hard-DRC findings, **16 opens and 11 dangling warnings**. Its nominal actual-copper model gives **96.48 °C** at a 60 °C local base and the retained 0.629222 W allocation. The stated lower-conductivity/thicker-board sensitivity gives **112.44 °C**, exceeding the 110 °C project allocation before measurement uncertainty. Do not promote this as a completed repair.

[Dimensioned review drawing](generated/review.svg), [PNG](generated/review.png), [LAND STEP](generated/LAND.step), [TIM STEP](generated/TIM.step), [native candidate PCB](variant/power_p03.kicad_pcb), [native receipt](variant/receipt.json), [exact local reroute ledger](relocation-clearance-plan.json), [thermal analysis](generated/analysis.json), [native collisions](generated/verification.json), [sealed handoff](handoff.json).

## Actual source and package

The immutable source is the fully routed P03 **42addb43b8cd1062e37cf1947e47f09fc0a3be940806f597d30586f41241617b**, with its actual schematic, component selections, construction, heatmap and native zero-ERC/DRC/parity/opens receipts copied under `sources/`. A separate 71-file CAD context preserves the actual source bodies, both PCB faces, THT tails, mount heads, controls, case and return hardware. The positive-link STL is also copied and hashed. These are historical captured inputs; later canonical routing does not silently refresh them.

Source U10 is **LT3090IDD#PBF**, DD 3×3 mm DFN, **B.Cu at native (192.5,128.5)**. P03's native origin is (100,100) and housing datum (168,108), so the translation is **(+68,+8)**: original U10 housing XY is **(260.5,136.5)**. Treating native (192.5,128.5) as housing coordinates would model the wrong location.

The [manufacturer LT3090 Rev A datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/3090fa.pdf), printed p2, gives **DD θJC =5.5 K/W**, with exposed pad11 electrically **IN**, required to be soldered to the PCB. Printed p33 specifies EP **1.65±0.10 ×2.38±0.10 mm**. The model injects heat over the minimum 1.55×2.28 mm EP while retaining the actual native copper pad. The I-grade operating junction maximum is 125 °C; **110 °C is the project allocation**, not a manufacturer rating. The package metric is a reference, not a guaranteed complete-path upper bound.

U10's live EP node is **RAW_N22**, not AGND. U11 is independently checked as the same DD device, **F.Cu** with EP11 **RAW_N17**. No U11 temperature pass is inherited. A TIM touching U10's outward-facing plastic while it remains on B.Cu cannot use the package's exposed-pad θJC path. No plastic-top or AGND substitute is credited here. Direct manufacturer PDF download timed out; the official parsed primary document was used, with no invented local PDF hash.

## Preserved failures

The baseline has no RAW_N22 pour. Its actual local heat path consists of small B/F/inner traces and remote barrels, with no declared RAW_N22 B.Cu sink under the first available lateral land. Both mesh runs reject a powered EP with no TIM connection; they produce **no physical temperature estimate**.

`history/zone-only/` preserves a native-zero B-zone-only trial. The authored polygon was not equivalent to filled copper: the saved fill stopped at Y130.399932 because foreign routing cut the neck. The larger proposed TIM also overlapped **C32's actual through-hole lead reserves**. That trial is rejected.

`history/rejected-no-move-via-bridge/` preserves the attempted no-move bridge with **47 native findings and one open**. Proposed vias hit existing under-EP signals and U8 front pads. Its exploratory thermal matrices are explicitly rejected as evidence of an electrically valid construction. No source geometry or TIM conductivity was invented to turn these trials into passes.

## Separate relocation candidate

U10 moves to **F.Cu native (194.2,129.3)**, housing **(262.2,137.3)**, using the actual stock F-side DD footprint geometry and original U10 net/pin identity. The source B-side package is removed in this variant; front EP access is real in the saved variant, rather than a hidden model assumption. Nominal front courtyard gaps are ~0.17 mm to L3, 0.40 mm to R17 and 0.20 mm to C32. All other component poses stay fixed. The P03 owner found no additional connector/port constraint on this trial.

The variant adds **four 0.60/0.25 mm direct EP vias and two field vias**, plus actual RAW_N22 fills on the four inner layers and B.Cu. Every original nonremoved route object is preserved. **22 enumerated local track/via objects were removed for clearance and must be deliberately reconstructed**, including N19 output, SET/reference and quiet AGND connections. Original NREF_FILTER routing is preserved. The input/SET/output decoupling loop must be rebuilt and checked by the electrical owner; the 16 opens are not waived. Native clearance consistency is not a functional LDO-loop proof.

The added fields end at native X194.75, before the existing U8 thermal field at X197; this final candidate does not borrow P12/AGND copper or modify U8's TIM geometry. Any future electrical reroute or merged board must renew the actual copper model and relevant return-path analysis.

| Interface, mm | Native XY bounds | Housing XY bounds |
|---|---|---|
| Bare aluminum land, top Z5.28 | 190.1,127.7 →193.75,131.4 | 258.1,135.7 →261.75,139.4 |
| Insulating TIM cut | 189.1,126.7 →194.75,132.4 | 257.1,134.7 →262.75,140.4 |
| Proposed retained-floor window | — | 256.9,134.5 →262.95,140.6 |

Land size is **3.65×3.70 mm**, TIM **5.65×5.70 mm**, with 1 mm nominal edge inset. The separate CAD land extends from base upper Z0 to Z5.28. The collision TIM reaches the lowest matched PCB bottom Z6.3; the nominal thermal gap is **1.22 mm at PCB bottom Z6.5**. Actual board-bottom range 6.3…6.7, incoming pad thickness, shims, bow, contact load and compression must be matched as an assembly. No force bending or solder-mask insulation is assumed.

The LAND STEP is an **addition for a future integral machined base boss**, not a loose post held against the existing base. The axial aluminum calculation assumes that integral construction. Frozen T01 is unchanged; the complete base revision, machining/attachment review and multi-pad clamp/deflection proof remain future integration work.

The candidate retains the existing TIM direction: **Henkel/Bergquist GAP PAD TGP6000ULM, sheet2195667, nominal1.524 mm**, identified in the copied T01 material packet. Its 6 W/(m·K) conductivity and dielectric test values are typical; minimum conductivity, received condition and assembly isolation are unapproved. The 1.5 mm-gap sensitivity assumes an actual pad that spans that gap under an approved compression condition; a thinner unmatched pad cannot be represented by a fictitious TIM bridge. Certified aluminum, surface finish, wear, contamination, pressure and flatness still require manufacturing controls. The metal stays floating CHASSIS and electrically insulated from RAW_N22. Anodize and solder mask receive no primary insulation credit.

## Thermal result and native geometry evidence

The sparse network uses **actual saved RAW_N22 fill polygons, pads, tracks, all physical via bores and matching plated barrels**. It contains no AGND heat path, solid-copper via-fill credit, FR4/air heat-transfer credit, fictitious sink or numerical gmin. The source is injected on the actual package face for each saved PCB. The model includes the 5.5 K/W package reference, axial aluminum-land term and separately declared interface assumptions.

At grid320, only **8.629 mm²** of the **13.505 mm²** nominal metal land lies under actual matching B.Cu. Nominal energy shares are ~13.85 K/W via barrels, 8.15 sheet spreading, 23.80 TIM, plus ~3.52 EP peak above mean, package5.5, land2.34 and assumed interface0.8. The network-energy shares are not independent series resistors; the report preserves their energy identity and KCL residual.

Nominal inputs are copper385 W/(m·K), TIM typical6, gap1.22 mm, interface0.8 K/W and nominal1.6 mm PCB. The illustrative sensitivity uses copper350, **unverified** TIM4, gap1.5, interface2 and a **1.76 mm engineering PCB-thickness allocation**, preserving the actual copper thickness and enlarging dielectric spacing. It is not a manufacturer-guaranteed enclosure. Refining160→320 changes nominal peak path by ~0.69 K/W; two meshes do not bound discretization/model error. Package/solder spreading and radial via-cap conduction remain unbounded.

All **seven native Manifold checks** clear as declared: required geometry104.155 mm³ agrees with STEP volume; component/tail, link/return and modified-case intersections are empty; 0.008 mm³ witnesses prove the land, actual front U10 reserve and actual C32 tail reserve were included. Missing geometry or a forged empty collision row fails the independent artifact gate. Obstacles include all506 actual captured electrical components, both faces, THT leads, mount-head requirements and the retained controls. Nominal empty intersections do **not** establish XY manufacturing fit: TIM-to-R34 and TIM-to-C32-tail gaps are only ~0.20 mm, and require an approved combined placement/lead-trim/die-cut/registration tolerance budget or relief. Fasteners, clamp force, local PCB deflection, seating and service loads remain unqualified.

## Acceptance still required

For the retained 0.629222 W allocation and a 60 °C base, total junction-to-local-base resistance must be **≤79.46 K/W before uncertainty**, or **≤76.28 K/W** with an illustrative 2 °C expanded uncertainty allocation. At65 °C base/2 °C uncertainty it must be ≤68.34 K/W. Those are derived project allocations, not measured limits or guaranteed materials. The current sensitivity exceeds them. Whole-path acceptance is **Tbase,upper +Pupper·Rpath,upper +expanded uncertainty ≤110 °C**; all four required measured/bounded inputs remain null.

Required work is actual local electrical rerouting and renewed zero-open native checks; qualified received C50 wall/annulus/web/fill/cap microsections; actual TIM thickness/compression/pressure/flatness and isolation testing; a validated junction-temperature measurement method and whole-path resistance/uncertainty measurement; actual P03 total-heat/base/ambient testing; then cold/hot, mounting, load, power-cycle and service checks on the source-bound assembly. A PCB surface reading, JEDEC θJA or thermal shutdown is not a junction qualification. Measurement on live RAW_N22 must use a suitable electrically isolated sensor/instrument arrangement. The floating chassis policy remains unchanged.

The CAD/PCB variant, drawings, native logs, numerical inputs and portable mutation tests are sealed in `handoff.json`. Solver tests are optional via `AFX_THERMAL_SOLVERS=1`; source/artifact checks are mandatory and require no native tools or downloads. All canonical-board, frozen-kit, fabrication, physical-fit and thermal-qualification flags stay false.

Reproduction uses KiCad10, OpenSCAD/Manifold and a Python environment with CadQuery/NumPy/SciPy/Matplotlib. Command completion generates the **routing-incomplete draft**; it does not waive the recorded opens or qualify the thermal path.

```sh
python3 -m hardware.cad.a12.thermal.candidates.u10.candidate --kicad-cli /path/to/kicad-cli
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10.generate
python3 -m hardware.cad.a12.thermal.candidates.u10.verify --openscad /path/to/OpenSCAD
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10.analyze
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10.draw
python3 -m hardware.cad.a12.thermal.candidates.u10.handoff
python3 -S -m unittest hardware.cad.a12.thermal.candidates.u10.test_candidate
```
