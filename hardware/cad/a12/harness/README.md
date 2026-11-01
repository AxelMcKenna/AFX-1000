# A12 harness development

The input feed now has specific component candidates in `input-feed.json`: MEAN WELL GST60A12-P1J, the retained PJ-102AH jack, JST VHR-2N housings/SVH-41T-P1.1 contacts, and Alpha 5858 AWG16 PTFE wire. Nothing has been purchased, crimped, powered or qualified. The positive 5 V leads and protected-output fanout remain separate unfinished assemblies.

The new near-source receiver is a private E19 extension, not an adopted operating
board. `proposals/processor-awg18-ear/` source `d55f9e48` adds J13 at housing
(188,100)/(188,104), a 14 × 12 mm ear, and real power/ground fills while preserving
all 84 prior complete footprints. Native ERC/DRC/warnings/parity/opens are zero.
`receiver_ear_fit.py` clears 15 local native cases. Its explicit inherited-H4
seating control retains the original 0.0163646 mm³ expansion overlap; only that
old intended support interface is excluded. A 0.00002 mm Boolean guard removes
an archived coplanar facet residual, with a separate proof that actual added
ear material never enters the exclusion. No physical seating tolerance is proven.

The source-exit search now has two actual 14-case native passes on the unchanged
J4 pads and isolated R58 source `fed47258`. The refined candidate uses positive
R10/angle7.5°/Z25.25 and return R16/angle−42.5°/Z31.75. Bare/insulated solids,
wire pair, source bores, electronics, power hardware, case and positive controls
are checked. This proves the local exit only. A downstream positive-link obstacle
rules out the simple planar continuation. The old east-pair trial is
rejected by 28.6584 mm³ hardware interference. The lower full-route trial is also
rejected: 188.29/208.28 mm conductor lengths, a wire crossing and actual component
hits. Both failures and the local passes are retained in the verified 323-file
full capture `generated/source-and-ear-native-review-1d507c891ec41ea2.tar.gz`
with its exact hash manifest.

The selected three-dimensional continuation now also clears **21 full native
geometry cases** in `generated/receiver-full-route/verification.json`.
The positive wire uses an exact R9.7 upward S-lift and tangent circular pieces;
the return uses a continuously certified cubic with radius lower bound
9.70943 mm. Both exceed the unchanged 9.6393 mm minimum. Proposed complete
conductor lengths, including the stated board/tail allowances, are
85.1908/78.2821 mm before unallocated cut slack and strain relief. The seven
millimetre receiving stubs retain 3.1 mm bare length at each board face.
Native cases include separate bare/insulated solids, flat insulation cuts,
source and receiving solder reserves, both actual minimum 2.1 mm bore pairs,
H9 post/head, electronics, case, power hardware, the wire pair and seven
nonempty controls. Independent raw log/STL review and all 606 current
source/evidence hash checks pass. Own PCB material is omitted from the general
obstacle union only with explicit common-frame endpoint-bore checks and a
whole central-tube height proof above the two PCBs, including the receiving
1.76 mm thickness allocation. Tails use the correlated solder/trim reserves,
not free-wire spherical endcaps below the floor.

Exact source/evidence is preserved by
`generated/full-receiver-route-native-8dcfe975e507e163.tar.gz` and its manifest,
which identifies the required 323-file parent capture above. All 607 reconstructed
file hashes were independently verified. This geometry pass does not qualify
forming, cut slack, strain relief, the solder process, the 2.4 A electrical
network or physical fit. E28's retained electrical opens remain unresolved.

The separate supported-ear source `27563a7a` adds only board-only H9 at
(182,97.2), preserving all 85 preceding footprints, original routing and outline.
Its native findings are zero. Independent integer polygon checks prove no pad,
track, via or filled copper enters the full 3.8 mm metal-exclusion disk on any
of four copper layers; only H9's empty NPTH is exempt from the native pad-object
rule. The extra hole/keepout changes real fills, so previous PDN results do not
transfer. J13's input target is 2.4 A: the known 1 A Seed and 0.764 A LED provisions
leave 0.636 A in other branches/reserve. Actual branch routing/return coupling
must replace an ideal source-star assumption.

`receiver_support_fit.py` checks a private Ø7.2 mm post from Z2.7 to the Z6.5 PCB
seat, with a blind Ø3.2 mm insert reservation and unselected M2x4-class fastener.
The post/head, minimum H9 bore, solder reserves, case and other hardware clear;
the actual floor bond is 4.06986 mm³. The supported shell remains one connected
surface with the same two inherited collapsed binary-STL triangles as the
unchanged-shell control. Its production mesh and strength remain unqualified.
The full support check deliberately fails: the proposed vertical tool envelope
hits the **actual DIG copper link**, with an independently isolated identical
11.35085 mm³ intersection. Removing only a cover would not resolve access.
Assembly/removal order or alternate access, exact insert/fastener/material,
retention, strain relief and physical tolerances remain open. No canonical
case or prior sealed packet is changed.

The owner has authorized a larger enclosure with a 20% space/headroom target.
The separate `../enclosure_growth/` starts at 334 × 188.4 × 45.6 mm shell size.
Its new control-board/shaft and thermal interfaces must be established before
any of this 38 mm-shell route evidence can be reused at changed endpoint poses.

The separate E19 receiver in `proposals/processor-awg18/` is now an actual native
PCB candidate, **52dcb485**, with 3.4 mm lands, 2.2 mm holes and 4 mm spacing.
J1 positive remains at housing (44,47,8.1); return moves to (44,51,8.1).
Raw native ERC, DRC, parity, opens and warnings are all zero. Independent review
proves every other complete native board node/footprint and all 76 component pin
maps unchanged; only the J1 schematic value/footprint binding changes.
`receiver_proposal.py` builds it and `receiver_review.py` verifies it.

`receiver_fit.py` passes **11 native local geometry cases** against the actual
electronics, all switch body/lead boxes, case, controls and power hardware.
It conservatively retains the inherited 11.31 mm service height and 3.15 mm tail
reserve. Separate common-frame wire stubs fit only the two actual minimum
2.1 mm finished bores, with maximum pretinned OD1.4 mm, 0.3 mm relative centering
and explicit insulation-cut allowances. These are unapproved manufacturing
requirements; receiving bends, solder process and retention remain unfinished.

Actual E19 distribution is a newly identified electrical gap. The explicit
`receiver_power.py` ideal-contact trace-centreline diagnostic gives J11 positive
drop **67.87 mV at 35 µm copper/100°C**, or 33.93 mV at 70 µm, under the retained
1 A Seed and 0.764 A LED provisions. These are scenarios, not resistance bounds;
actual pad spreading, finite barrels and ground are not included. E19 has no
selected copper stackup. Thus the older lumped wire comparison's approximately
7.09 mV LED endpoint margin cannot qualify the actual board. A separate private
distribution repair and finite positive/return extraction are required.

`output_route.py` now constructs a complete two-ended trial from analytic
tangent-continuous lines/arcs, with true minimum radius and chord/sample bounds.
Total conductor lengths including board penetration and trimmed tails are
**192.32/192.63 mm**, before slack. Wire-pair clearance screens positive, but the
Z31/27.5 route intersects the pad-switch bank, so the command correctly exits
nonzero. No native full-route pass is claimed. Moving a loose path through the
switch leads or ignoring the newly found board voltage drop would not complete
this harness.

The exact receiving/native/11-case evidence, rejected full-route screen, original
E19 power diagnostic, coherent P03 `db83a26f` nine-case body evidence and separate
whole-unit heat packet are captured in
`generated/receiver-and-distribution-review-3b4b9bc12ba59470.tar.gz`. Its manifest
binds all 305 files; archive and current bytes were independently verified.
All physical, complete-harness and fabrication-release flags remain false.

Run `python3 -m hardware.cad.a12.harness.analyze`. The report binds the actual inlet/P03 native connector positions and source files. It rejects a net/pin change or incompatible insulation diameter. The manufacturer PDFs are kept external; their exact hashes and source URLs are recorded rather than redistributing them.

The [adapter specification](https://www.meanwell.com/Upload/PDF/GST60A/GST60A-SPEC.PDF), revision 2026-04-03, specifies 12 V/5 A and measures voltage at the output plug. Its ±3% tolerance already includes setup, line and load regulation. Adding the temperature coefficient over the project's 0–40°C adapter ambient and a conservative full 120 mV peak-to-peak adverse ripple displacement gives a conditional 11.43–12.57 V interval. This does not bound startup or load-step droop. Its cable drop must not be added a second time. The 12.6–16.2 V overvoltage trip range is not an output-peak clamp. P1J's 11 ±0.5 mm plug versus the jack's 9.5 mm insertion depth still requires shoulder, rear-panel and engagement review.

The [Alpha 5858 specification](https://www.alphawire.com/en/products/wire/hook-up-wire/premium/5858) gives insulation diameter 1.8542–2.2098 mm and a 10-diameter bend radius. The maximum requires a 22.098 mm radius; because the source does not identify inner-surface versus centerline radius, the CAD allocation adds one wire radius and requires a 23.2029 mm centerline radius. It fits the [VH nonretainer housing/contact insulation range](https://www.jst.com/wp-content/uploads/2021/08/eVH.pdf), but exceeds the retainer housing's 2.2 mm limit. VHR-2M is not an interchangeable substitution. The selected AWG16 contact is SVH-41T-P1.1; SVH-21T-P1.1 is for smaller conductors. Crimp tooling, this actual wire construction and pull/section inspection still need approval. The connector's +85°C limit includes current-induced temperature rise.

The two native headers reverse the lateral pin order. A straight coplanar two-wire arrangement would cross. `input_route.py` now provides a conditional three-dimensional route for the two individual wires, with opposite vertical lifts at that crossing. It reads the native pin/net positions, checks the actual 0°/180° header orientations and binds the complete case/component snapshot. Reproduce it with `python -m hardware.cad.a12.harness.input_route --openscad /path/to/OpenSCAD`.

The current candidate allocates a wire exit 22 mm along each connector's mating direction and 3.85 mm above the PCB face, with a 0.65 mm isotropic position allowance. These are **unapproved interface requirements**, not manufacturer dimensions. The sampled free spans are approximately 51.5 and 51.0 mm, with minimum nominal centerline radii of 45.5 and 46.8 mm against the conservative 23.2029 mm requirement. The native solids include the maximum insulation diameter, position allowance and conservative tessellation. Five checks require actual wire solids, clear wire-to-wire/case/electronics intersections and a nonempty deliberately colliding witness. The two intended connector housings alone are excluded from the electronics intersection; all other bodies remain. Results are source-bound in `generated/input-route-verification.json`; subsequent PCB, case or route edits require a new check.

A clear allocated envelope does not approve the mated exits, manufactured bend radius, forming fixture, connector service access, retention, strain relief, terminations or the operating harness. No clips or forming fixture are implemented yet. The 100 mm per-conductor limit is an electrical screening maximum, not a frozen wire-cut drawing; the sampled free span excludes the terminated lengths. At that length, catalog nominal DCR plus an assumed copper temperature coefficient gives about 3.625 mΩ per pair at 85°C. DCR is explicitly nominal; it cannot certify the separate 5 mΩ measured-wire allocation. Likewise, four environmental-test contact limits total 80 mΩ and two catalog jack contacts total 60 mΩ, but neither establishes the assembled hot/lifetime resistance.

The older public VH catalog provides the conservative +85°C screen used here. The [current series page](https://www.jst-mfg.com/product/index.php?lang=2&series=262) lists −40 to +105°C; applicability to the selected exact part and process must be reconciled before changing that screen. Individual dimensional drawings/CAD require a manufacturer form with contact details and terms. That form has not been submitted; no exact mated wire-exit tolerance is inferred from the simplified public illustration.

The complete 0.36 Ω feed remains a conditional P03 scenario. Acceptance needs actual plug-to-protected-input voltage/current measurements across the load/temperature corners, uncertainty, connector/fuse heating, crimps/solder/retention, startup/droop, and coordinated overload/fault behavior. No source interval, dimensional fit or resistance calculation changes a physical-release flag.

The protected DIGITAL output now has a separate **rejected local escape study**
in `output_escape.py` and `generated/output-escape/`. It reads actual E28 J4
pad/net identities and the current PCB thickness (1.62 mm), and models the selected
Alpha 3079 AWG14 pair. Its 21 mm quarter-circle centreline radius exceeds the
19.8374 mm conservative requirement. Both curves turn toward housing +X at
−17.3° in XY, beginning 3.1 mm above the nominal board face. Maximum insulation
diameter, 0.65 mm position allocation and 0.25 mm obstacle clearance are included;
termination, forming and strain-relief dimensions remain unapproved.

The numerical body screen includes both native component faces, radial
capacitors and switch lead reserves, with a continuous-arc sampling-cover bound.
The actual six native checks detect required wire geometry and the deliberately
colliding 0.008 mm³ witness. The wires clear one another and the declared
electronics envelopes, but intersect the case/control mechanism by about
5.1203 mm³ and the power-link/return hardware by about 19.7707 mm³. The failed
STLs include their actual collision locations. The command exits nonzero for
this result; it is not an installed route or evidence that every possible route
is impossible.

```sh
python -m hardware.cad.a12.harness.output_escape \
  --openscad /path/to/OpenSCAD
```

The next repair must coordinate the actual wire/termination or supporting
geometry, followed by new body, case, hardware and bend checks. The receiving
E19 J1 is still an unselected two-pin header interface; no complete AWG14 mate,
branch/fanout, cut/strip drawing, electrical loss, assembled-current or lifetime
qualification is inferred from the local escape. Source and native evidence
hashes are recorded with the failed study. Subsequent board changes require a
new binding.

Two separate thin-insulation studies use the current manufacturer
[Alpha 6717 specification](https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=6717).
The proposed AWG14 41/30 tinned conductor retains catalog nominal DCR, with
2.4892 mm maximum insulation diameter and a conservative minimum centreline
radius of 13.6906 mm. `output-wire-6717.json` records the reviewed external PDF
hash and conflict with an older ten-diameter specification. Stock applicability,
current/temperature limits and maximum DCR remain unqualified; the BOM is unchanged.
The thin-wire quarter-circle trial still intersects the case by 0.5659 mm³ and
hardware by 0.1102 mm³. A leftward 3D bend with explicit curvature and
integration-error bounds intersects the case by 2.9724 mm³ and hardware by
26.7073 mm³. Both are rejected local routes.

The isolated `proposals/j4-ear/` project moves actual J4 pads to housing
(165.3,137)/(165.3,143) mm, adding a 3.3 × 10 mm PCB extension and 3 mm lands.
`output_port_proposal.py` builds the copied native project. Native KiCad finds
zero ERC, hard DRC and parity issues, but **47 opens and 77 warnings**: one
additional open versus its source. Native semantic comparison confirms only J4
and Edge.Cuts change; the other 254 footprint contracts, zone contracts and stack
match. Connectivity cannot qualify the new force/return access resistance.

`output_port_fit.py` checks the actual extension and solder/lead reserves against
the full assembly. The extension has its expected 56.1000 mm³ volume and clears
the nominal case/hardware, but the new top joint reserve intersects the ANA
return retainer by **14.8688 mm³**. With explicit ±0.2 mm XYZ position allocation
and 0.25 mm clearance, hardware conflict is 27.1463 mm³ and case conflict is
2.3975 mm³. The 0.008 mm³ positive witness is detected. These port-only checks
exclude curved wires. The first rejected 100-file input/evidence packet is
`generated/rejected-j4-ear-a7433d16a956dd8d.tar.gz`, with its hash manifest.

`output_retainer_proposal.py` builds a separate offset-head retainer from the
original STEP geometry. It preserves the lower stem/base attachment, moves the
head 4 mm along the ramp and adds a PEEK arm. Four valid single solids pass STEP
volume roundtrip. Native checks show the nominal joint interference is removed
and component bodies clear. This proposal is **also rejected**: its head meets
the actual return-bar corner (0.2604 mm³) and positive-link support (46.4624 mm³).
The ear's clearance envelope still intersects the stem by 0.1223 mm³ and fails
case clearance. Only the intended coplanar stem/base seating face is excluded
by 0.00001 mm. Stock, strength, creep, shock and manufacturing remain unqualified.

```sh
python -m hardware.cad.a12.harness.output_port_fit --openscad /path/to/OpenSCAD
python -m hardware.cad.a12.harness.output_retainer_proposal
python -m hardware.cad.a12.harness.output_port_fit \
  --offset-retainer --openscad /path/to/OpenSCAD
```

Both fit commands currently must exit nonzero. The operating PCB, return kit and
housing remain unchanged. A coordinated support/PCB/harness repair or more
headroom needs investigation. The retained 38 mm shell is a project dimension;
the original RMX-1000's specified [overall height is 57 mm](https://pioneernz.co.nz/pages/specifications-rmx-1000).
Those scopes differ: the project's external thermal base already adds height,
and knobs/control travel also belong in the complete envelope comparison.

The separate 54 mm-shell study now clears **nine native local-escape checks**
on captured P03 `42addb43` / E28 `7b5227fd`. It uses the proposed 6717 wire,
14.5 mm bend radius, 13 mm straight lift and a +X turn. Panel-mounted bodies,
switches, the lever and their proposed mount heights move together by 16 mm;
floor/rear electronics retain their native datums. Native witnesses require
the raised wall and actual raised switch lead to exist. Returning the shell to
38 mm deliberately causes a 277.22 mm³ intersection. Inputs/evidence are saved
in `generated/raised-shell-local-escape-b9a96f3068e07e09.tar.gz` (93 bound files).

This local result does **not** complete the harness. `output_length.py` reads
actual E19 J1 pad positions and its complete allocated mating-body reserve.
After the tested escape, even a straight unobstructed remainder to anywhere
in that reserve requires at least **183.20/186.09 mm**, exceeding the selected
150 mm installed-length limit. The pad-to-pad lower bounds are 189.21/190.90 mm,
before unmodelled source bare wire, termination and strain slack. Its command
exits nonzero. A different receiving layout, complete route or independently
accepted wire/loss allocation is required; no length limit has been changed.

`height_envelope.py` also exports the actual shell, knobs, keys, selectors,
lever sweep and feet. Their native Z extrema give **87.6 mm overall** for the
38 mm shell and **103.6 mm overall** for the 54 mm shell, using nominal unloaded
feet. The former 66.8 mm interface value only reaches the plastic shell.
Neither shell choice nor complete revised enclosure has been approved or
physically verified. Forming fixtures, source and receiving termination,
fanout, hot/lifetime resistance and mechanical service requirements remain open.

The complete historical height/length audit is preserved as the parent capture
above plus `generated/height-length-audit-e12afe5af5f33f3e.tar.gz`. Its JSON manifest
binds all 102 reconstructed inputs/artifacts and both archive hashes; the delta
avoids duplicating the same PCB/source capture. A later copper-only E28 C40 repair
is independently checked in `generated/c40-native-contract-independent.json`:
all complete footprint/pad, edge, zone and board-setup contracts remain equal.
That geometry equivalence does not approve its changed copper resistance or
alter the harness length rejection.

```sh
python -m hardware.cad.a12.harness.output_escape --wire 6717 \
  --radius 14.5 --angle 0 --straight-mm 13 --shell-height 54 \
  --openscad /path/to/OpenSCAD
python -m hardware.cad.a12.harness.output_length \
  hardware/cad/a12/harness/generated/output-escape-raised-shell
python -m hardware.cad.a12.harness.height_envelope --openscad /path/to/OpenSCAD
```

The read-only `output_port_search.py` now screens a bounded alternative J4
region: housing X125…154, Y111.2…124.2 mm, on a 0.25 mm grid. It uses all 859
actual native copper-pad shapes, existing tracks/vias on every copper layer,
both populated faces, source solder/lead reserves and the existing 4.2 mm lands,
2.2 mm holes and 6 mm pitch. Round buffers are circumscribed and native pad
approximation error is reserved. Zones are intentionally excluded from this
placement screen: a later candidate must quantify actual antipad/copper loss.

On E28 `2830c887`, none of the 6,201 sampled sites meets both copper and body
clearance. The largest foreign-copper gaps are 1.374 mm for positive and
1.537 mm for return, versus 2.26 mm required. A separate 377-open development
baseline with long nonforce routing removed has 126 positive/270 return sites
that pass the copper screen, but still **zero body-clear single sites** and no
eligible pairs. An independent complete native footprint/pad/edge/zone/setup
comparison proves that its bodies remain the same before reusing their packet.
This separates legacy-track blockage from actual component crowding.

The proposed position (145.5,115.4)/(151.5,115.4) is blocked by U25, U27, C46,
R105 and R109; it has not been emitted as a PCB candidate. Further work requires
a coordinated component/termination/region change. This sampled regional screen
does not prove global or continuous impossibility and does not replace native
DRC, source/return extraction, a complete wire route or physical testing.
The original bound capture is `generated/port-search-2aaab9f74bc663be.tar.gz`.
Current and clean-baseline diagnostics/review images are under `generated/port-search/`
and `generated/port-search-clean/`. The screened source, rules, polygons, solver
versions and artwork hashes are recorded; no operating PCB is changed.

The matched-algorithm original/clean comparison is preserved in
`generated/port-placement-comparison-9d1a0174e6f4e6da.tar.gz`; its manifest binds
the required parent archive and all 82 reconstructed source/evidence files.
It also captures the independent native geometry-equivalence proof and actual
clean-baseline PCB/pad polygons. These bytes reconstruct exactly. The numerical
screen uses NumPy 2.5.4/Shapely 2.1.2 and is a placement investigation, not DRC.

Separate smaller-wire proposals are recorded in `output-wire-6715.json` and
`output-wire-6716.json`. The current primary Alpha specifications give AWG18
6715 a maximum 1.7526 mm insulation diameter and AWG16 6716 a maximum 2.1082 mm;
the conservative centreline radius requirements are 9.6393 and 11.5951 mm.
Catalog DCR is nominal, not a guaranteed maximum, and received-stock bend
specifications remain unconfirmed. Neither proposal changes the operating BOM.

`output_electrical.py` compares these proposals in the retained complete P03
lumped source-to-load network, preserving the loads, source intervals, endpoint
targets and both positive/return paths. A **proposed measured 8.5 mΩ total per
lead at 100°C** gives a weakest DIGITAL endpoint of 4.907088 V in that conditional
model. Its resistance boundary is approximately 11.9952 mΩ per lead. The proposed
200 mm installed length, wire/joint/board-escape allocations, receiving interface
and fanout are unqualified. This does not prove the coupled actual PCB/ground
network, current/temperature performance or assembled hot/lifetime resistance.

`output_formed.py` adds actual-source bare conductor, the flat insulation cut,
native J4 joint/lead reserves and a separate common-frame source-hole check.
It retains the actual J4 pads and the 38 mm shell, a 10 mm bend radius, 0.65 mm
external position allowance and 0.25 mm clearance. The first constant-angle
AWG18 study clears the case, wire pair and allocated source bores but intersects
R58 beside the source joint (0.245977 mm³) and the power hardware (2.719811 mm³).
The hardware includes a lower DIGITAL copper section at Z17.8; treating that
link as entirely at Z20.5 would hide a real collision. The complete rejected
capture is `generated/rejected-formed-6715-7502e26a018c1276.tar.gz`.

Raising only the positive-lead end plane to Z24 clears the hardware and case,
but introduces a 26.3301 mm³ wire-pair collision. R58 still fails, and the pair
overlap also invalidates the required nonoverlapping insulation-volume witness.
That rejected study is captured in
`generated/rejected-formed-6715-positive-raised-39ba984bfbaef3ef.tar.gz`.
The joint-only and wire-only electronics checks explicitly separate the R58
problem from the wire bend. Complete routing, receiver/fanout design, strain
relief and physical acceptance remain unfinished.

The next compact-return study uses a 9.7 mm return radius, still above the
9.6393 mm conservative centreline requirement. At Z24 it clears wire-pair and
hardware checks but hits a control support at Z25.6 (0.064410 mm³); this rejected
capture is `generated/rejected-formed-6715-compact-return-87c2f82137619551.tar.gz`.
The `balanced-return` profile lowers positive/return end planes to Z23.8/23.6.
Against canonical E28, every local wire check clears except the existing R58
joint conflict. Its evidence is captured by
`generated/formed-6715-balanced-canonical-9d25c3ed381db668.json` and its stated parent.

The separate actual E28 R58-only source `fed47258` moves R58 by −0.2 mm Y.
Independent complete parsed-node comparison verifies that every track, via,
zone, edge, stack and other footprint is unchanged; restoring that one Y
coordinate reproduces the complete original R58 footprint. Native pad/barrel
containment remains intact without trace repairs. Raw native checks retain
**45 opens/76 warnings/zero hard DRC, parity or ERC findings**. This source
remains an electrically incomplete development candidate.

Using that actual source, `balanced-return` now passes **all 14 local native
cases**, including separate joint and wire electronics intersections, full
power hardware, case/control supports, wire pair, actual source-board bores,
bare/insulation volume checks and three nonempty witnesses. The 38 mm shell
and native J4 pose stay unchanged. The tight numerical switch-lead gap after
the stated position/clearance/sampling reserves is approximately 0.0106 mm;
forming fixtures and actual minimum bend radii remain to be qualified.

The fresh `output_length.py` audit includes the 3.1 mm source bare length above
the board face. Relaxed pad-to-pad lower bounds are **152.03/158.36 mm**, below
the separate proposal's 200 mm limit. This only avoids an immediate length
rejection: intervening obstacles, receiving bend/board penetration, strain
slack and complete fanout remain unmodelled. E19 J1 is still the original
unselected header with 1 mm holes; the proposed AWG18 core is nominally
1.2192 mm and has no qualified receiving interface.

The exact 14-case source/proof/evidence packet, full conditional electrical
comparison and length audit are preserved by
`generated/formed-6715-r58-local-clear-77bc675f1bdb193a.tar.gz` and its JSON
manifest. Its stated parent plus delta reconstruct all 150 bound files, whose
bytes were verified. No canonical PCB/BOM, complete harness or physical-release
flag is promoted by these local results.

```sh
python -m hardware.cad.a12.harness.output_formed --profile balanced-return \
  --source-candidate hardware/electronics/rail_disconnect/revision28/generated/r58-joint-work \
  --openscad /path/to/OpenSCAD
python -m hardware.cad.a12.harness.output_length \
  hardware/cad/a12/harness/generated/output-formed-6715-balanced-return-r58
```
