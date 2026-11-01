# NC265 — actual NF265 ports and force-strain prototype

This is a **connector/strain interface proposal for a NEW149×39mm NF265 PCB**. It preserves the frozen NC01, NP01, NP01-P1, FR01 and NF electrical sources. It does not complete the other259 PCB components, full-unit fit, wiring, electrical behavior or fabrication qualification. All physical/electrical/fabrication flags remain false.

The exact copied NF05R265 source is seal `f53cdb06d5f8c717ddc7b0b077bedf5ff1b855561d742b6e0197465467738cad` (90 files). The corrected NF05H261 source is `6459d8269a46bbc6f1c1558bb8dbfc68c12082f9cbaefcf1a4865cbbdc182a02` (114 files). All204 files plus both seals were copied and checked before/after capture. [identity-review.json](identity-review.json) enumerates the actual28 changed identities/pin maps and four added parts C100/R98/R99/U58; the current265 has199 passives. No old233 placement, old30-wire net labels or generic2.54mm header geometry is inherited.

## Stable input for the new board layout

Use [ports-v2.json](ports-v2.json), SHA `2aa7689628f87de2b5d635b127849e6baa0d09c048eaf81dbc20aed55bcf3e6b`, and [ConnectorCandidates.pretty](ConnectorCandidates.pretty). Every physical pin is checked against the actual265 native netlist. The export's top-level `/` label prefix is explicitly reconciled; NC4's exact unconnected node is preserved. This is a source-bound contract, not a cryptographic signature or electrical approval.

| Ref | Selected candidate / interface | Pin1 local(u,v) | Pitch / pad arrangement | Catalog reference mated projection → project receiving maximum |
|---|---|---:|---|---|
| J1 | JST **B30B-PHDSS / PHDR-30VS / SPHD-002T-P0.5** |5,17.5|2mm; odd1[0,0], even2[0,2], last30[28,2]|8.8→10.0mm |
| J2 | Direct-solder Alpha6715 **18AWG** N19 in/out |68,21|5mm; Ø3.8lands / nominalØ2.2bores|3.1mm allocated front solder/strip envelope |
| J3 | JST **B2B-PH-K-S / PHR-2 / SPH-002T-P0.5S** |57,30|2mm|8.0→9.0mm |
| J4 | Direct-solder Alpha6715 **18AWG** N12 in/out |79,21|5mm; Ø3.8lands / nominalØ2.2bores|3.1mm allocated front solder/strip envelope |
| J5 | Same PH2 clamp pair as J3 |100,30|2mm|8.0→9.0mm |
| J6 | JST **B2B-XH-A(LF)(SN) / XHP-2 / SXH-001T-P0.6** |123,17.5|2.5mm|9.8→10.5mm |

All rotations are0°. Nativeu→worldX172+u; nativev→worldZ3.5+v; positive front normalw→worldY180.5−w. This is proper Rx+90°, with the component copper face atw0. FR4 receiving thickness remains1.44..1.76mm. A maximum received body/mate envelope is a **project incoming inspection requirement**, not an invented manufacturer tolerance. Public primary catalog nominal dimensions and these receiving bounds are separate fields in the JSON. Body profiles/maximums, exact mating/key alignment, crimp/strip dimensions, retention and life require supplier/measurement acceptance.

J1.4 retains a physical header pin but its housing contact and wire are **omitted**, leaving29 populated wires. J1.7 is **ABS_AUX_FAULT monitor OUTPUT ONLY**,1µA complete external-load requirement; it is not a reset input and must not be externally driven. J6 is guarded12V plus **MODULE_INPUT_GND**, serving only the two TMR primaries/input capacitors. It must not be tied to quiet AGND on the NF board. J1.2 still carries RAW5/AUX/control return current and is not an ideal zero-impedance star.

The actual electrical current requirements remain provisional: RAW5 guarded35.132243mA; AUX11mA normal/14mA fault allocation; their arithmetic shared AGND subtotal49.132243mA is not a complete coupled/feedback current bound. J6's normal primary input screen is174.129mA at9V;20µF is only the nominal input-cap subtotal and inrush/fault current is unbounded. PHD/XH3A atAWG22 and PH2A atAWG24 are catalog test conditions, not current approval for every chosen wire. Low-level/dry-circuit reliability and the actual crimp process remain open.

The XH and PHD public catalogs reference1.6mm boards; PH specifies0.8..1.6mm. Thus the1.76mm maximum receiving case is **not supplier-approved**. Obtain a coherent fabricator thickness contract or explicit connector approval before adoption. Nominal3.0/3.4mm post tails also cannot be assumed to meet the rear1.5mm **trim plus solder** envelope across that thickness range. Controlled post-solder trimming and fillet gauges are required; original untrimmed pins are not credited.

The general rear-SMD1.2mm field is a default frame requirement for this interface-only scene, not a claim that all265 parts fit it. The later root NF06P layout's14 named rear1.9mm capacitor exceptions are a separate placement proposal and need their own actual-tail/body/seat checks. They are not adopted into this packet. Likewise these ports deliberately require repacking old left WIMA/TO263 sites; old233 would clash and is not asserted to fit.

## Real local force strain geometry

[geometry.scad](mechanical-v2/geometry.scad) contains the actual two-part prototype. The [two analytical pilot-hole STEP parts](mechanical-v2/BREP/BREP.json) are valid single OCC solids; their polygonal native STL volumes differ by<0.0064% from the analytical cylinders/planes. Both actual native part STLs are closed, consistently oriented, nonzero, nondegenerate, connected boundaries. The STEP files retainØ1.6mm tap pilots; no modeled cylinder is represented as a qualified M2 thread.

[Dimensioned drawing](mechanical-v2/BREP/NC265-strain-drawing.svg) · [review PNG](mechanical-v2/BREP/NC265-strain-drawing.png) · [all exact datums](mechanical-v2/datums.json).

The machined material candidate is **MCAM Ketron1000 natural unfilled PEEK**. The manufacturer labels its material properties indicative and unsuitable as guaranteed design allowables; they do not prove threads, dielectric performance, creep or pull strength. No conductive/ESD/glass-filled substitute is assumed.

Two posts at(61,21)/(90,21) use OD6.0nominal /6.1mm maximum receiving, normalw0..5. The lower bridge occupiesu58..93/v17.5..21/w4.8..13; the cap occupiesu58..93/v21..24.5/w5.3..13. Actual post-to-cap normal gap is0.3mm. Four channels are at u68/73/79/84,v21. The cap grips straight insulated wire before any bend. Source joint/PCB/carrier reaction loads still require qualification; solder joints are not strain anchors.

The prototype channel isØ1.65 for a measuredØ1.70 wire. For fabrication trials, measure **each** wire and machine its paired semicircular channel to measuredOD−0.05mm. Proposed±0.01mm measurement and±0.02mm machining produce0.02..0.08mm diametric interference. These are **trial requirements**, not approved MPPE compression, grip, pull, creep or damage limits. A universal1.65mm bore must not be assumed correct for the full1.651..1.7526mm wire OD interval. No pull-force or torque guarantee is invented.

The drawing's nominal/incoming dimensional cases do not establish complete hot dimensions. Differential PEEK/FR4/steel expansion over the29mm post span, manufacturing registration, clamp preload and PCB/carrier bending must be qualified together. No catalog room-temperature material property is promoted to a guaranteed installed tolerance or load limit.

Mount holes H101/H102 are nominalØ2.6 /finishedMIN2.5mm, with all-layerR3.7 copper/track/via/pad/pour exclusions. The native keepout annulus omits only the nonconductive NPTH core; strict hole clearance must still reject copper there. The unrelated packing square around a mount is not the actual post solid. At H102 the actual maximum post beginsu86.95, versus J4's solder receiving maximumu86.4:0.55mm gap. The local native test retains0.2mm relative registration plus0.25mm clearance, leaving0.10mm modeled margin. The low-component allowance beneath the bridge is≤3.0mm front projection and requires actual future part checking.

Actual fastener candidates are **Accu SPP-M2-5-A2** mounts, **SPP-M2-6-A2** cap screws, and **HPW-M2-A2-BL** washers. Primary catalog maxima: screw headØ4/H1.72; washer OD5, thickness0.25..0.35, ID2.2..2.34mm. Incoming screw length±0.1mm is a project requirement, not a published catalog guarantee. Nominal mount/cap thread overlaps are3.05/2.15mm; receiving corner ranges2.79..3.41 /2.0..2.4mm. Received thread form/engagement, torque, pullout, creep and repeated service remain unaccepted.

Rear mount head+washer can extend2.07mm behind the board, to w−3.83/worldY184.33 at maximum FR4 thickness. This is a **local fastener exception** distinct from the1.5mm rear lead policy and lies below the upper seat. Cap hardware reaches v26.57/worldZ30.07. Actual controls, case, PCB tails and every other component must be checked against these solids during full-unit adoption.

The direct-force footprint requires finishedMINØ2.1mm and a tinned conductor bundle≤Ø1.4mm,0.3mm relative centering and0.005mm geometry reserve, leaving0.045mm idealized radial gauge margin. The old1mm holes fail. Specify front bare/fillet projection≤3.1mm from the component face using an insertion jig, then rear trim **including solder**≤1.5mm; strip length, wetting, wicking and thermal process must be developed together. Four Alpha6715 BK005 leads are separately and permanently marked N19_P03/N19_E28/N12_P03/N12_E28. Source and remote18AWG terminations are not yet implemented here.

Four≤1mΩ solder joints per rail are an **unmeasured allocation**, not a solder property. Wire hot resistance is additional; nominal7Ω/1000ft is not a guaranteed hot upper bound. No complete5mΩ path or endpoint-voltage pass is claimed. The wire supplier bend minimum is8.763mm; this proposal retains the prior **9.6393mm hard receiving minimum**, with9.7mm chosen for future bends. Complete force routes and remote strain are not designed by the straight local prototype.

## Native evidence, including retained failures

[prototype-v3](prototype-v3) is an actual native **connector-only** fixture: six electrical footprints/40 physical source pads, two mechanical NPTHs, four copper layers,16 clip KOs plus8 strain KOs. Strict all-severity KiCad10.0.7 DRC has0 violations/0 opens. Those counts do not mean a265-component circuit is connected. The intended future full board has six layers and needs its own24 clip/12 strain keepouts and native checks.

Two actual native copper mutations are rejected: copper inside the omitted NPTH core fails **hole_clearance(required0.2500/actual0.0000mm)**; copper in the outer strain annulus fails **items_not_allowed**. The core polygon has at most1.392µm extra radial construction allowance beyond the nominal1.3mm hole radius, wholly inside the separately enforced0.25mm hole clearance. No broad copper-pad exception is used. The earlier native fixture's two self-NPTH keepout errors and eight invalid-library-table warnings are preserved in `prototype-v2`; NEWv3 fixes the annular core construction and version7 table. The nonfatal native Python wxApp assertion/debug messages are retained in the build logs; the processes returned0 and did not use unowned `Flip`, `SetProject`, automatic UI reopening or any security override.

The initial force-pair receiving gap was0.20mm, below0.25. Its real nonempty native witness is retained as `old-pair-failure.stl`. V2 moves only J4 by+1mm; no solder receiving envelope is shrunk.

The original18 local Manifold cases have **14 passes and four retained strict contact failures**. Those four outputs are only zero-volume shared-plane facets and are not accepted as production meshes. A fresh audit proves every one of9,268 triangles lies entirely in **one same convex declared contact mask**, avoiding a per-vertex union loophole. NEW checks remove only±20nm around these finite own contact surfaces: component/post front seats, nominal back washers, cap washers/thread tips, and base/cap seat. All actual parts/ports/datums/STLs stay byte-identical. All four new comparisons are empty, and **all five deliberate1000nm intrusions retain their expected980nm depth** (9.8×10⁻⁶mm³). No general plane, factory tolerance or finite-overlap exemption is granted. [Original](mechanical-v2/native-run1/verification.json) · [facet audit](mechanical-v2/facet-boundary-audit.json) · [new nine checks](mechanical-v2/native-guards/verification.json).

The SCAD API exposes `nc265_strain_world()` for the actual nominal local assembly and `nc265_strain_receiving_world()` for the conservative post/body/fastener receiving solids. `nc265_interface_receivers_world()` supplies the six body/mate/solder receivers. Root full-unit integration must include all other parts and preserve only justified own-seat correlations. This packet does not inherit full-unit fit, thermal, stiffness or airflow performance.

## Control-wire exits and remaining work

[control-fanout.json](control-fanout.json) gives29 local candidate exits. The exact rigid transform of the old reference curves preserves radius/distance; NC4 is removed and every remaining net is remapped from the actual265 contract. A **fresh** [406-pair continuous replay](fresh-control-proof/proof.json) using captured original interval/Taylor-bound source succeeds; the deliberately unstaggered same-column pair fails. Radius14mm exceeds Alpha3049's13.462mm supplier minimum. No sampled minimum is used as proof.

The assumed wire exit normal plane w10.0 and intrinsic0.24mm relative-position requirement still need actual mate/crimp/loom validation. This is not proof of entry through an opaque housing, a restrained harness, remote destinations or clearance against the new265 components/control/power scene. Generic full-wire end spheres are not a substitute for measured correlated termination geometry.

Before adoption: root must finish the NEW265 component placement, actual pads/drill/land/copper routing, connector/force regions and complete later board thickness/stackup; recheck all rear tails and named1.9mm cap exceptions; verify full-unit new PCB/posts/controls/wires; route actual source/return/clamp/control and force harnesses; qualify hot resistance/ground coupling, inrush/branch faults, crimp/retention, solder process, strain strength/creep, material and thermal/airflow effects. This source does not absorb later FPC91, E28 routing or protection changes implicitly.

## Verification without overwriting any seal

```sh
python3 -m hardware.qualification.boards.nf_connector_receiving265.audit
python3 -m unittest hardware.qualification.boards.nf_connector_receiving265.test_nc265
.venv/bin/python -m unittest hardware.qualification.boards.nf_connector_receiving265.test_nc265
```

The15 portable tests include actual source/pad geometry, wrong J1.7 mutation, real native KO failures, required-mesh absence, forged-empty-with-actual-STL, flipped-triangle rejection, convex-mask bridge rejection, all five finite controls, matched hardware/bore arithmetic,29-wire isometry and continuous certificate subset, analytical/faceted part consistency and false-handoff-promotion rejection. Builders refuse existing outputs. Do not run `capture.py` as a verification or overwrite the packet. Fresh native comparisons and CAD exports require new `--output` paths and the recorded native tools; raw original failures remain part of the evidence.

`final-execution-v2` is the source-current four-command audit/test gate under Python3.9.6 and3.12.13. The earlier `final-execution` records14 tests before the final handoff-contract test/gate was added; exact earlier source copies are retained there and it is historical evidence, not the source-current seal gate.

The copied KiCad footprint sources retain **CC-BY-SA4.0 with KiCad's design exception**, preserved in the library LICENSE. Public manufacturer documents retain their original ownership. No restricted JST drawing form or license was accepted and no personal information submitted. Primary references: [PHD](https://www.jst-mfg.com/product/pdf/eng/ePHD.pdf), [PH](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf), [XH](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf), [PEEK](https://www.mcam.com/mam/52982/AEP-Ketron%C2%AE%201000%20PEEK_en_US.pdf), [mount screw](https://www.accu.co.uk/pozi-pan-head-screws/9241-SPP-M2-5-A2), [cap screw](https://www.accu.co.uk/pozi-pan-head-screws/9242-SPP-M2-6-A2), [washer](https://www.accu.co.uk/metric-flat-washers/179343-HPW-M2-A2-BL).

`NP01-primary-page-index-erratum.json` corrects only the old KEMET source page index to actualPDF5/9, CJ0.80±0.15mm. The original0.95mm body +0.10mm project seat =1.05mm projection is unchanged; no numeric height erratum or parent-seal rewrite is asserted.
