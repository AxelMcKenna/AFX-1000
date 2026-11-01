# A12 repaired-board integration

The owner has now authorized a larger enclosure with roughly 20% space/headroom.
The new private [shell/lid candidate](enclosure_growth/README.md) starts at
334 × 188.4 × 45.6 mm, preserving width and adding 20% depth/height. The
original A11/A12 kit and its source-bound checks remain the comparison baseline.
New control-board/shaft positions, supports, thermal base/feet/attachments,
assembly access and wiring require renewed integration; larger dimensions alone
do not resolve the electrical or cooling holds. Separate conditional thermal
work is in `housing20percent/`; no old thermal result is inherited. The newer
loaded [coupled metal-chassis model](thermal/coupled_housing20/README.md)
still fails the 65 °C base screen. A separate
[installed-cooling requirement](thermal/installed_cooling_h20/README.md)
quantifies the stronger underside heat transfer needed under its 20% heat
stress, reduced fin exposure and doubled-joint-resistance scenario. These
are conditional calculations; actual metal construction, controls' local
temperature limits and physical thermal tests remain open.

The larger-housing work now includes eight shell/lid cases, ten lever-travel
cases and nineteen local receiving-post/tool-access cases. TC02 uses the new
front bay for the touch controller and clears fifteen primary local fit checks;
the raised audio-jack row clears seven local evidence cases. The renewed
EI02 combined scene clears all 45 required native cases after relocating J29 on
the actual electrically closed `3b2a8197` PCB. The later
[enlarged base/control assembly](thermal/enlarged_base_pot/README.md) passes
122 native cases and 13 portable tests. Its actual STEP parts and component
3MF retain explicit nominal TIM/shim and mounting contracts. The corrected
R1 PCB has a separate fifteen-case fit check, and the new positive-link/wire
proposal retains its old wire failure and nine passing lifted-wire checks.
The later [fan/base assembly](thermal/enlarged_base_forced_air/README.md)
establishes all 162 modeled geometry conditions: 161 direct native passes and
an exact 60-pair/10-control recovery of one combined check whose two execution
failures remain recorded. It provides the actual 960-pin base, tray and
component review assembly; it does not adopt the later PCBs, link/wire or fan.
The [internal-air budget](thermal/air_path_budget/README.md) exposes excessive
restriction in the old Noctua/guard scenario. A [higher-pressure Sunon study](thermal/forced_air_sunon/README.md)
now supplies an exact-part prototype candidate and new guard/port requirements,
with 20 analytical checks across the two packets. Installed airflow and local
control temperatures remain unverified; a higher-temperature pot fit study is
now [sealed separately](pot_stack_high_temp/README.md), with 106 native checks
and explicit panel-web, washer/thread and temperature holds.
The new [fan-protection schematic](../../qualification/boards/fan_protection/README.md)
has 18 parts, zero native ERC/parity findings and 13 targeted checks. It corrects
the old J3 source suggestion: that P03 header is test only, so an operating-force
branch must be designed. The health/temperature interlock, PCB and complete
source/harness remain unfinished.
The [fan-health firmware candidate](../../qualification/boards/fan_health/README.md)
has 12,647 host assertions passing and an actual AVR build. The sealed FH02
68-part native circuit passes13 targeted checks. The
[FPC01-M1 fan PCB](../../qualification/boards/fan_health/composite_mount/README.md)
now has84 parts, actual all-layer mounting keepouts, zero strict native
ERC/DRC/parity/connectivity findings and six regression checks. Installed fault
behavior remains unqualified. The newer
[parallel-branch pressure comparison](thermal/airflow_operating_point/README.md)
includes NF03C/FH02's proposed37.406 W heat provision and explicit2.42 A DIG
capacity proposal, and rejects AP02's original
125 mm² base metering aperture in the low-speed scenario. The separate
[318 mm² meter](thermal/interior_airpath_meter318/README.md) passes 54 native
geometry cases and 16 portable checks; its wider approach now enters the
conditional coupled-flow model. Actual loss, split and local temperatures
remain unverified.
The [unified UA01 assembly](enclosure_growth/unified_airpath/README.md) now binds
the captured P03/R1/E28 boards, AP03 airpath, revised return hardware and positive
links. Its original42 checks retain41 passes and a blocked-guide failure;
eight new service-state checks pass after the lid-mounted guide is removed.
Root independently verified all1,913 sealed files and the saved-evidence audit.
It excludes the newer NF/fan boards and changing E28 routing.
The separate [FR01 front-bay receiving assembly](enclosure_growth/front_bay_receiving/README.md)
includes the captured233-part NF and84-part fan board geometry, revised mounts
and local wire exits. Its final30 mounting checks and nine local-wire checks
pass; the generic NF mating-connector collision remains a retained rejection.
Selected newer NF parts, complete wire paths and the changing E28 board require
a refreshed assembly receipt. Its floor-port projection also enters AP04 as a
separate area sensitivity, with no installed-flow claim.
The actual [NF03P placement](../../qualification/boards/startup_negative_circuit/placement/README.md)
and [NF04R READY successor](../../qualification/boards/startup_negative_circuit/ready_integration/README.md)
are separate development proposals requiring routing, full-unit fit and native
E28 adoption. None of these results qualifies installed cooling or operation.
Complete wiring, electrical/thermal/structural validation and physical tests
remain open. See the
[larger candidate record](enclosure_growth/README.md) for current status; the
paragraphs below describe the preserved original-size kit and earlier trials.

Current checks restart through the
[single-operation isolated runner](controlled_restart/README.md), using the
verified pinned Linux image. Mac CAD runtimes installed by the automation are
in reversible quarantine after repeated startup crashes. A fresh Linux Boolean
probe and the NF four-cap rear-tail check with its positive control pass;
no Mac CAD app was opened for this restart.
The earlier restricted macOS signing commands could not access OS signing
services. A later [signing-service recheck](qualification_reviews/macos_signing_recheck/README.md)
validates the unchanged official2026.10.27 app, with Gatekeeper accepting its
notarized Developer ID. Its three native Manifold self-tests passed at that
earlier checkpoint; the later startup failure supersedes its current usability.
Historical receipts stay
unchanged, and no design check is inherited from this tool self-test. No macOS
security override is used.

A12 preserves the 334 × 157 × 38 mm A11 housing and its original source kit. It allocates a **complete replacement P03 supply**, with a 160 × 45 mm relieved outline at (168, 108, 6.5) mm. A 110 × 65 mm replacement conflicts with the old LED-driver bay. Lower corner notches clear the existing lid screw bosses; a plain rectangle in this location does not fit.

The [whole-unit heat audit](thermal/whole_unit/README.md) now exposes a cooling
failure under the retained provisional load allocations. A 35.4315 W all-inside
planning screen gives 95.36–99.51 °C peak base at assumed h3/emissivity0.8 and
40 °C ambient. The earlier 10.5578 W supply-loss map is incomplete for whole-unit
cooling. Holding a 65 °C base requires substantially better heat transfer or a
proven lower power envelope; no local TIM result qualifies the present passive
assembly. The 60-file audit seal and numerical controls were independently
checked; actual power/installed-boundary upper/lower fields remain null.

Further private fanless studies are in `thermal/power_budget_audit/`,
`thermal/loss_options/`, `thermal/fanless_feasibility/` and
`thermal/fanless_top_fins/`. Root verified their complete sealed input/artifact
hash maps. They do not establish a lower power envelope or approved cooling.
The existing-height underside fins alone are inadequate. A private metal-lid/
sidewall/top-fin study can exceed 35.43 W at a 65 °C scenario only under favorable
boundary/contact assumptions; realistic seam sensitivity and reduced exposed
fin faces can fail, and all tested 60 °C cases fail. No fan, metal lid or new fin
geometry has been adopted into the frozen enclosure.

The [harness record](harness/README.md) now includes a near J13 receiver extension,
two local 14-case source-exit passes and a separate H9 support candidate. The
selected complete source-to-J13 wire pair also clears 21 fresh native geometry
cases on the existing 38 mm housing; forming, strain, electrical distribution
and physical qualification remain separate. This does not establish a complete
power-distribution network or fit at changed larger-housing endpoints. The H9
post/head fit clears locally, but its original axis hits the actual digital
copper link. The later wider-ear/relocated-axis candidate clears nineteen local
post/head/tool cases; exact driver, removal sequence, wire retention and
physical access remain to be validated.

The top assembly allowance is 12 mm above the 1.6 mm PCB; the bottom allowance is 3 mm including assembly protrusions. The thermal candidate adjusts the board bottom from Z6.3 to Z6.7 with measured shims. Component reserves cover that complete height range: the bottom allowance leaves 0.5 mm minimum to the 2.8 mm floor, and the top reaches Z20.46 maximum after including a conservative, unaccepted 1.44–1.76 mm fabrication-thickness range around the native 1.6 mm PCB. These are dimensional allocations. Component courtyards, actual selected-part heights, fasteners, connector mating/access, wires, cooling and manufactured tolerances must still replace or validate them. The ordinary plastic-support board check seats the PCB at its nominal Z6.5; the external-base variant removes those old supply posts locally.

```sh
python3 -m hardware.cad.a12.generate
python3 -m hardware.cad.a12.verify --openscad /path/to/openscad
python3 -m hardware.cad.a12.verify_thermal_integration --openscad /path/to/openscad
python3 -m hardware.cad.a12.verify_repaired --openscad /path/to/openscad
```

`integration.scad` reuses A11 housing, control geometry, button travel, lever sweep and actual obstacle envelopes. It provides a conservative collision check and an intentionally unrelieved positive control, which must collide with the lid bosses. A pending native PCB cannot be approved through a reserve-only check.

Native OpenSCAD finds empty intersections for the relieved supply board/reserves and for the actual E23I2 rear-inlet board and allocated assembly envelopes against the existing housing, controls and electronics. The plain rectangular supply positive control does collide. The result is bound to source hashes in `generated/verification.json`; changing the actual board, height allowances, housing or control geometry requires another review and run. The 0.00001 mm seating translations exclude intended planar support contacts; they do not excuse solid interference.

The [E23I2 passive inlet](../../electronics/input_protection/inlet_revision2/README.md) uses the original rear jack, switch and mounting positions with a real native five-component replacement. P03 owns the input guard. The side-entry power connector reserve includes a conservative complete mated assembly, rather than only the bare header. Actual connector tolerance review and the cross-bay harness to P03 remain open. The old E23 component bodies and old main supply are removed from A12's new integration; their source revisions remain preserved.

The [input harness record](harness/README.md) selects actual adapter, housing, contact and wire candidates and identifies the reversed pin order between the native headers. It now includes a proposed 3D crossover with separate wire envelopes, explicit unapproved mated-exit requirements, a bend-radius screen and five native geometry checks. Actual exit dimensions, wire forming/retention, hot resistance and startup qualification remain open. The positive 5 V leads and protected-output fanout still require complete routing and terminal-cover design.

The Würth top-side M3 return terminals in `interface.json` are provisional E28 interface data. The actual native footprint, fastening stack, supports, busbars and complete return geometry remain under review. No joint resistance or physical fit is established by those nominal dimensions. The main source and disconnect owners must agree a native source-bound interface before integrating it here.

The disconnect mounting plane is now Z5.0, 0.4 mm higher than A11. Its four printed posts and all inherited reserves move together; A11 remains unchanged. The raised candidate clears the checked case/control/electronics geometry with a ±0.2 mm vertical component-envelope allocation. The return bars/retainers must use the corresponding terminal planes; this is an internal mounting change, not permission to bend stiff bars into place.

`repaired.py` separately extracts the actual current P03/E28 outlines, mounting holes and courtyards on **both populated faces**. Every part has an explicit assembled-height requirement, and through-hole leads have a separate 1.5 mm trimming envelope. A separate same-board box/cylinder screen catches bodies touching another component's protruding lead. The review caught a 10 mm film capacitor on P03's underside; it is now top-mounted with pad coordinates/nets preserved. It also caught E28's underside SOIC comparator height, repaired with the actual lower-profile TSSOP order code and land pattern. `verify_repaired` has nine native cases: nominal PCB material, component-to-case/other-electronics clearance, mutual board integration, complete switch electronics and deliberately colliding controls. Component projections include the P03 Z6.3–6.7 adjustment, declared PCB thickness ranges and E28's ±0.2 mm vertical allocation. The nominal PCB-material check does not prove correlated support/thickness/warpage tolerances. Receipts are named `generated/repaired-e28-z5.00-u0.20-verification.json`; source changes invalidate them. Actual MPN heights, complete mating/operating wire envelopes and manufacturing acceptance remain unapproved, even when the declared envelopes clear.

`a12_switch_electronics()` adds every B3F-1000 switch at the current A11 center and fixture rotation, including its allocated lead/solder region. The 10 × 10 mm local plan reserve, 4.5 mm body projection and 4.5 mm downward lead/solder requirement are recorded in `interface.json`. At the nominal carrier datum, the lead reserve starts at Z22.7. Native checks require the full bank's expected volume and a 1 mm³ lead-region witness. The lead/solder projection is an assembly requirement requiring trimming and inspection; carrier seating/tolerances and complete loose control wiring remain unverified. Holder/key geometry alone did not cover these electrical parts.

`thermal-integration.scad` composes the [external thermal base candidate](thermal/README.md) with the retained plastic floor and its existing standoff connections. Only the local thermal-land, supply-support and return-post windows are removed. The lower shell attachment has actual clearance bores and proposed captured-nut pockets/assembly slots. Sixteen native checks cover the metal, retained carrier, return hardware and selected lower-shell fastener envelopes against their stated obstacles. The repaired board components are checked separately by the nine-case packet. Positive controls retain the unmodified floor, intersect a known return-bar location, and deliberately restore the old Ø6 mm countersink. The last produces a 2.329 mm³ collision with the selected conservative bolt-head envelope; the revised Ø6.6 mm countersinks clear. The checked carrier remains one connected closed triangle boundary after excluding two duplicate-vertex, zero-area binary-STL export faces; that is a geometric connectivity check, not a strength assessment. Evidence is bound to the exact source solids in `generated/thermal-integration-verification.json` and must be regenerated when the thermal design changes.

This candidate adds an external plate, fins and feet below the original housing. The 66.8 mm thermal-interface dimension ends at the plastic shell and excludes controls; it was previously described too broadly as assembled height. The [native full-height audit](harness/generated/height-envelope/verification.json) includes knobs, keys, selector caps and release-lever travel: the retained 38 mm shell gives **87.6 mm nominal overall height** with the present feet and knobs. The separate 54 mm shell study gives 103.6 mm and has not been adopted. Bumper compression and manufacturing tolerances remain unverified. The base alone is approximately 1.14 kg. This does not preserve the original overall height or mass. Fastener dimensional/assembly tolerances, thread engagement, structural retention, actual repaired-board components and all wiring remain open. Nominal return-hardware clearance against the case/base/controls does not establish its clearance from the changing PCB components or resistance retention under thermal expansion. The thermal screening calculations and nominal solid intersections do not establish powered cooling performance.

`candidate_fit.py` checks a separate, electrically closed P03 project using its
actual native PCB/components and private staged SCAD packets. It preserves the
canonical sources and shared generated packets. Nine inherited board/body/
switch/case checks clear independently for U102 source `138931e3` and restored
eight-EP U10 source `f94c8005`, each against E28 `2830c887`. Both populated faces,
506 native electrical parts, mounting-head requirements and nonempty witnesses
are included. Receipts are under `generated/candidate-fit/`. The new thermal
LAND/TIM, complete copper power links, loose wiring and physical/process checks
remain separate. Later native routing or component movement requires renewal.

The 18-case historical evidence and complete native source/proof files are
captured in `generated/history/closed-supply-body-checks-b4971acefa7162f1.tar.gz`.
Its JSON manifest identifies the required parent capture and all 150 exact
reconstructed file hashes; reconstruction has been independently checked.
Run a new candidate with `python -m hardware.cad.a12.candidate_fit
hardware/electronics/power_distribution/p03/candidates/NAME --openscad
/path/to/OpenSCAD`. This regenerates workspace-specific include paths.

The repaired AUX front-cell source `37fd6109` independently clears the same nine
cases against E28 `2830c887`, with **507** actual component records. Exact selected
capacitor projections are C106 2.9 mm, soft-termination C113 1.60 mm and C110
1.0 mm; the generic case heights would understate the first two. Changed/new
candidate MPNs require matching selections and an exact geometry resolver.
The checker binds the actual candidate PCB and raw native ERC/DRC reports,
and captures their complete source/artifact maps. This evidence is preserved
by `generated/history/aux-front-body-checks-c02fbcd1e9c7b3b4.tar.gz` and its JSON
manifest, using the explicitly identified parent archive. All 120 reconstructed
file hashes were verified. These body checks exclude the new thermal contact
pieces, complete power links and harness, and do not qualify physical fit.

The separate `thermal/candidates/u102_stronger/` packet now also replays the
actual repaired `37fd6109` copper and checks its real LAND/TIM addition against
the captured 507-part assembly, power links, case and controls. Root independently
verified all 285 sealed file hashes and seven actual solid/empty/witness cases;
27 portable audit, mutation and height/integration checks pass. The sensitivity
reference is 107.30 °C at an **assumed** 65 °C local base plus 2 °C allowance.
Actual package, material, contact, whole-unit heat and base-temperature bounds
remain missing, so this is not a guardbanded thermal pass. The proposed new
floor window and thermal pieces have not modified the frozen kit.

The new coherent P03 composition `db83a26f` combines the actual AUX repair and
restored U10 contact/routing source. All nine fresh body/control/case cases clear
with 507 component records, zero same-board envelope overlaps and actual raw
native ERC/DRC/parity/opens all zero. Root checked every source/artifact binding.
This does not inherit either separate thermal result: actual combined copper,
whole-unit heat and all interfaces still require validation.

The AUX count erratum is explicit: source `37fd6109` and its composition retain
nine direct EP barrels and **two** named adjacent AGND barrels, not three.
The unchanged actual thermal parser/report uses 17 domain AGND vias/9 EP vias;
its numeric result did not include an invented third barrel. The incorrect
historical drawing/README count is identified separately in
`thermal/whole_unit/errata/U102-37fd-adjacent-via-count.json`; the immutable
285-file packet stays preserved. Restoring the old third site would violate
native clearance to the newly selected C106 pad and has not been done.

Physical fit is unverified. This development allocation is not a fabrication or qualification release.
