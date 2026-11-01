# Repairs following the three-board audit

Qualification remains withheld. These are separate development revisions; they do not replace the pictured boards in the original Q02 capture plan. No physical board has been powered or measured. The [repaired-assembly bench matrix](REPAIR-BENCH.md) covers the replacement boards and their complete installed interfaces; it contains requirements, not test results. The [E27 audit corrections](ERRATA.md) supersede its affected historical interpretations.

The later [FPC01-M1 fan board](../../qualification/boards/fan_health/composite_mount/README.md)
is now sealed with84 parts, zero strict native ERC/DRC/parity/opens/warnings and
six mounting/copper regression tests. All84 complete footprints and all unrelated
track/via trees are preserved;16 native keepouts implement the four clip sites
on every copper layer. Physical mounting, supply fault response, PDN, noise and
cooling remain unqualified. Root independently verified its90 bound files.

The [negative rail circuit index](../../qualification/boards/startup_negative_circuit/README.md)
tracks the newer standalone sequencing, absolute-AUX cutoff and UV-recovery
work. The sealed261-part circuit corrects the two new START timer pin maps and
adds the correctly wired independent supervisor; its original four floating
monitors were already correct. Root verified all114 files and12 tests. Its UV
recovery, LED charge paths and external-output current ledger are addressed in
the newer sealed265-part NF05R circuit, whose13 tests pass; loaded cutoff and
shared-fault timing remain unqualified. The independent196-part passive review also identifies actual
footprint, tolerance and drift changes; it does not confer PCB acceptance.

The coherent E28 control-port repair reached11 opens with zero hard DRC/ERC/
parity findings. A subsequent audit found19 raw open-collector nodes feeding
ordinary logic. A new269-part receiving candidate adds seven triple Schmitt
buffers and seven bypasses; its first escape pass reached59 opens with zero
hard DRC/ERC/parity findings. That count is an intermediate routing result,
not a replacement of any sealed checkpoint or a whole-unit acceptance.

The sealed [FR01 receiving assembly](../../cad/a12/enclosure_growth/front_bay_receiving/README.md)
captures the older NF233/FPC84 geometry, mounts and local wire exits. Its final
30 mounting and nine local-wire checks pass; the generic NF mate collision
remains a retained rejection. Current NF/E28 circuits and complete harnesses
require a refreshed native assembly. The separate AP04 projection sensitivity
uses its1258.684mm² uncovered vertical projection without treating it as a
governing flow throat. All installed thermal/flow gates remain false.

The newer [NF03C negative startup circuit](../../qualification/boards/startup_negative_circuit/compact/README.md)
has 231 parts and 15 passing checks. Root independently verified all 98 sealed
files and freshly exported its native schematic: zero ERC errors, the same two
reviewed floating-ground warnings and exact pin/value parity. The independent
[review](../../cad/a12/qualification_reviews/nf03c/review.json) records one
narrative resistor-value erratum without editing the seal. PCB placement and
E28 integration are still required.

The [FH01 fan-health firmware](../../qualification/boards/fan_health/README.md)
now passes 12,647 host assertions and compiles for the actual AVR target at
1,760 bytes of code and 90 bytes of static RAM. The installed toolchain is
checked against its official archive. Actual controller hardware, full stack,
timing, partial-power and sensor/thermal behavior remain unqualified. Fourteen
portable monitor/temperature/air-budget tests are included in tooling CI.
The earlier tooling run has507 tests:504 passed and three optional skips. The
later [checkpoint CI run](generated/portable-handoff-ci/report.json) passes560
tests:557 passed and three optional skips, with451 selected inputs unchanged
before/after. A fresh
core build passes its other 35 CTest checks. Historical baseline tests now
verify exact captured bytes and explicitly deny current applicability; the
[capture audit](../../cad/a12/qualification_reviews/historical_sources/README.md)
retains the original 20-failure log and two unrecoverable historical files.

The [new branch pressure comparison](../../cad/a12/thermal/airflow_operating_point/README.md)
uses the NF03C/FH02 receiving37.406 W heat provision and explicit2.42 A DIG
capacity proposal, and shows that AP02's original
125 mm² base meter fails the low-speed flow comparison. The later
[318 mm² meter candidate](../../cad/a12/thermal/interior_airpath_meter318/README.md)
passes 32 main and 22 mating native checks, with 16 portable tests. Root checked
all 369 sealed files; its larger rear approach is included in the new coupled
flow comparisons. No geometry or conditional operating point qualifies
installed airflow or component temperatures.

The new [FP01 fan-protection section](../../qualification/boards/fan_protection/README.md)
contains an 18-part native schematic, zero ERC/parity findings and 13 targeted
checks. It explicitly supersedes the old FV01 source suggestion: P03.J3 is
test only, so a new operating-force branch is required. Source/return joints,
health/temperature interlock, PCB and installed fault behavior remain open.
The separate [HT01 control fit](../../cad/a12/pot_stack_high_temp/README.md)
passes 106 native cases while retaining explicit thread/washer, panel strength
and temperature holds. Root checked all 39 FP01 and 331 HT01 sealed file hashes.

A later sealed [E28 routing checkpoint](../../electronics/rail_disconnect/revision28/generated/u28-return-dual-plane-work/generated/handoff.json)
now has **32 opens, 82 warnings, zero hard DRC/ERC/parity findings** on PCB
`dd6a6f5a`. Root checked all 253 source/artifact hash bindings. Local logic-part
relocations and a wider board band free routing space; two ground-plane layers
reduce the E28-only return diagnostic to about 1.773 mΩ. This remains a partial
routing candidate: external contacts/bars/P03, quiet-ground coupling, latest
whole-unit CAD and physical validation are not qualified. The older 43-open
checkpoint below remains a preserved historical result, not the newest draft.
An unsealed later routing draft has reached 28 opens and 80 warnings after
three control connections and a real C38 ground repair. It is still in progress
and does not replace the sealed checkpoint or imply fabrication readiness.

The authorized larger-housing work now has separate actual 334 × 188.4 × 45.6 mm
shell/lid blanks with eight native cases clear. A source-derived panel map keeps
the low E19/E18/E20 stack fixed while raising panel-mounted parts. Moving the
fixed-Z lever, angle-sensor reserves and four support posts together by 7.6 mm
clears ten native local cases, including the swept travel and raised lid.
The old unshifted lever collides by 118.603 mm³ and remains a control.

The newer [pot/knob receiving candidate](../../cad/a12/pot_stack/README.md)
passes 32 conditional local checks after raising the knobs 0.8 mm, lowering
their screw axes and increasing ten panel bores to Ø9.5 mm. It retains actual
old bushing, axial-bearing and registration failures as positive witnesses.
Four revised knob meshes have one closed connected boundary each. Supplier
tolerances, exact pot/washer/screw selection, support, material/tapping/retention
and physical/thermal validation remain open. This is a later separate candidate;
the frozen EI02 45-case result does not automatically qualify these changes.

The [enlarged metal base](../../cad/a12/thermal/enlarged_base/README.md)
has 42 passing native records and 12 portable tests, including explicit nominal
TIM/shim interfaces. An independent audit identified foot thread-abstraction
wording and recapture/replay documentation defects. The frozen
[combined base/PS01 revision](../../cad/a12/thermal/enlarged_base_pot/README.md)
addresses both, with 122 passing native cases and 13 portable tests.
Root independently reviewed all 598 files, raw case logs and strict part/control
meshes. Original parent packets remain unchanged; whole-unit electrical,
thermal, structural and physical qualification remain withheld.
The [dual-fan tray prototype](../../cad/a12/thermal/forced_air_prototype/README.md)
passes 23 local native cases but changes the pin field and foot height.
The later [FI01 assembly](../../cad/a12/thermal/enlarged_base_forced_air/README.md)
establishes all 162 modeled conditions through 161 direct native passes plus
60 exact distributed intersections and ten controls for one combined check.
Both exit137 attempts remain explicit. The actual 960-pin base and tray have
STEP outputs and a 16-object review assembly; later PCB/link/wire/fan
substitutions are not inherited. The [AP01 air budget](../../cad/a12/thermal/air_path_budget/README.md)
finds the old fan/guard pressure scenario insufficient. The [SF01 comparison](../../cad/a12/thermal/forced_air_sunon/README.md)
selects a higher-pressure exact-part prototype candidate with new guard/port
requirements; its flow, current and acoustic figures are conditional.
Actual fan supply/protection/wiring, local control temperatures and fresh
installed cooling validation remain open. All fabrication release flags remain false.

The newer wide/access E19 `2145521e` has zero native findings and preserves
the other 85 complete footprints. Its fresh actual four-layer copper path is
about 4.8012 mm wide, rather than the old 0.7797 mm bottleneck. Root's 19 native
local ear/post/tool checks clear, including an open-lid Ø6.5 mm driver envelope
at the relocated H9 (182,92.2). The old axis still intersects the unchanged
digital copper by 11.35085 mm³. This closes the stated local geometry problems
for this candidate only; resistance/ampacity, strain, exact hardware/process,
lid removal and physical assembly remain open. Later physical fanout additions
need their own fresh geometry and electrical extraction.

The separate Trill C3 saddle corrects the old nominal 52 × 21 mm reserve to the
actual native 53.848 × 21.844 mm outline. Its local checks pass, but the frozen
EI01 combined scene reveals real saddle/C8, J29/return-retainer and rear-TS/
cassette interferences. The newer TC02 controller mount uses the added front
bay and clears fifteen primary local interference/fit cases. Root independently
checked all 25 TC02 evidence records, including the retained failed centering
sensitivity and blocked guide-installed tool access, and all 42 EI01 records.
The panel-map absolute touch
backer Z fields have a separate source-bound erratum; actual bases are Z34.6
and Z42.2. Whole-unit integration, connectors/electrodes, material, strength and
touch tuning remain unqualified. The high-end F06 adapter already uses the
Trill protocol; the older MPR121 adapter belongs to the separate budget build.

Raising the eight audio-jack axes by 0.8 mm clears all seven local rear-port
evidence cases without reducing the body classes, openings or external
clearance. Exact jack mating/fastening/wiring geometry remains open. The first
EI02 trial's 25.538 mm³ J29/bonded-pedestal clash is preserved as rejected
evidence. The final actual J29 PCB `3b2a8197` has zero native findings and
preserves the other 87 footprints and all foreign signal routes/vias.
Its combined scene clears all 45 required native cases, including the original
0.25 mm P03/E28 external-clearance cases, actual PCB bores, modeled wire pair,
rear jacks and open-lid tool access. Root independently verified 191 bound
hashes and all raw logs/STLs. This scene still binds E28 `fed47258` with
45 electrical opens and the old-size thermal base; no later E28/J8/metal-case,
complete-wiring, thermal or physical qualification is inherited.

The later [actual R1 repair](../../cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1/README.md)
selects WSLT2512R4700FEA, preserves 0.47 Ω and the 1 A Seed provision, and
uses its manufacturer land pattern at a new position. Its configured native
ERC/DRC/warnings/parity/open counts are zero. Root's
[independent source review](../../cad/a12/qualification_reviews/r1/review.json)
verified all 59 sealed files, the other 87 complete footprints, all 79 component
pin maps and the unchanged foreign routes and board configuration.
Its separate [fresh finite PDN](../../cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1-pdn/README.md)
uses the actual new copper and finite vias. Root independently checked its 28
files and recomputed all 96 saved fixture products and 960 quiet-reference
offsets. The known-load Seed copper loop is 21.519–21.883 mV before R1 under
the unaccepted coarse 100 °C model. The complete source-to-Seed guaranteed
voltage interval remains undefined because signed ground/contact/remote-load,
startup and process uncertainties remain open. This later PCB needs its own
combined mechanical adoption; earlier assembly and thermal results are not
inherited.

The later [actual R1/CP01 fit packet](../../cad/a12/enclosure_growth/r1_local/RESULTS.md)
passes all fifteen fresh pinned-Linux native cases: ten empty intersections,
four 0.008 mm³ witnesses and the real receiving-volume output. Root independently
checked all 132 files and reintegrated the raw outputs. Only the old R1 body was
excluded; other components and the external/board-height allowances remain.

The sealed private E28 U14-input repair `28c86cea` improves its finest analog
copper diagnostic to 2.95865 mΩ against the provisional 3 mΩ allocation. Root
independently checked all 86 bound source/artifact hashes, all 85 archive
members and the raw native reports: 43 opens, zero hard DRC/ERC/parity findings
and 66 warnings. Its E28-only digital return is still 2.24306 mΩ, exceeding the
entire 2 mΩ return allocation before external contacts and conductors. A direct
J8 return proposal requires new attachment, wiring and bulk-capacitor transient
analysis; no return-network or board qualification is inherited.

The separate [PB02 link/wire proposal](../../cad/a12/positive_links/proposals/dig-leg-y121p3/README.md)
clears the complete south-facing J8 receiving attachment after a 1 mm digital
mid-leg adjustment. The old positive wire fails the maximum covered-link screen
by 3.881 mm³. Its separate 1 mm curve lift passes nine new native cases while
preserving ports and the 9.7 mm minimum bend radius; its length bound increases
2 mm. All 32 part/envelope meshes pass strict integrity checks and 68 finite
section witnesses pass the existing area screen. This does not implement the
new J8 outgoing return wire or qualify C24 transient currents, contacts, strain
relief or the complete electrical return path.

The [larger-housing thermal study](../../cad/a12/housing20percent/README.md)
reduces the source-loaded base-only peak to 86.19–89.93 °C under its retained
35.4315 W/40 °C ambient scenario, still above the 60/65 °C screens. Separate
prescribed-base metal-lid/sidewall scenarios do not establish loaded coupled
temperatures or a bounded 20% margin. The new
[loaded coupled study](../../cad/a12/thermal/coupled_housing20/README.md)
includes actual lid apertures, rear/vent cuts and finite joints; all seventeen
loaded scenarios fail the 65 °C base screen. The nominal hot-cluster/full-fin
case is 71.32 °C. A separate bounded calculation requires approximately
h9.34 W/m²K uniform underside heat transfer to meet 65 °C at 1.2 × heat,
half effective fin convection and 0.2 + 0.2 K/W joints. This is a model
requirement, not installed cooling evidence or a selected fan. The PTV09
control family's +50 °C operating limit also requires separate local thermal
validation. All installed/physical cooling flags remain false. Original source
kits and historical sealed archives are preserved.

The newer private E19 J13 ear `d55f9e48` has zero raw native findings and clears
15 local geometry cases, including explicit inherited-H4 seating/witness
controls. Two searched unchanged-J4 source exits each clear 14 full native local
checks. Root independently verified and archived all 323 bound source/evidence
files in `hardware/cad/a12/harness/generated/source-and-ear-native-review-1d507c891ec41ea2.tar.gz`.
The same capture retains rejected eastern and lower full-route trials; these
local passes do not establish a complete source-to-receiver connection.

The later selected 3D J4-to-J13 continuation now clears 21 whole-pair native
geometry cases on the existing 38 mm shell, including flat insulation cuts,
separate bare/insulated solids, solder/trim reserves, both minimum PCB bore
pairs, all power/case/component obstacles and positive witnesses. Independent
raw log/STL review and 606 current source/evidence hashes agree. Its archive
`hardware/cad/a12/harness/generated/full-receiver-route-native-8dcfe975e507e163.tar.gz`
and manifest bind 607 reconstructed files using the named parent capture.
This is a geometric route, not forming/strain/solder/electrical/physical
qualification. The owner subsequently authorized a 20% larger-depth/height
enclosure study; changed endpoints and control-board poses require new checks.

The H9-supported ear `27563a7a` separately preserves all 85 preceding complete
footprints and all original board objects. Its zero native findings and full
four-layer 3.8 mm metal-exclusion polygon audit were independently checked.
The extra keepout removes actual copper, so no parent PDN result is inherited.
The private new case post/head and receiving solder envelopes clear locally,
but native tool-access checks hit the **actual digital copper link** by
11.35085 mm³, independently reproduced with isolated DIG-CU geometry. Assembly
or removal access, exact fastener/insert/material, strain relief, complete
2.4 A input/fanout/return behavior and physical qualification remain open.

The current coherent P03 draft `db83a26f` combines the actual AUX repair and U10
contact restoration with zero raw native ERC/DRC/parity/opens. Nine fresh actual
507-part body/control/case checks clear. The separate E19 receiver `52dcb485`
also has zero native findings and passes 11 local fit checks. Its larger direct
wire bores replace an unselected receiving-header assumption, but do not qualify
the solder process or full harness. A complete 192 mm trial wire pair is rejected
for switch-bank collisions, and actual E19 power distribution introduces voltage
drop omitted by the older lumped model. The exact evidence and rejected path are
captured by `hardware/cad/a12/harness/generated/receiver-and-distribution-review-3b4b9bc12ba59470.json`.

The [whole-unit heat audit](../../cad/a12/thermal/whole_unit/README.md) closes an
analysis-scope gap, not a thermal qualification gate. Retained provisional power
provisions give a 35.4315 W all-inside/no-export planning screen. The current
ideal base reaches 95.36–99.51 °C at assumed h3/emissivity0.8 and 40 °C ambient;
the former 10.5578 W map covers supply losses only. The passive cooling proposal
does not meet its 60/65 °C base scenarios at those conditions. Actual load and
heat-transfer bounds remain unproved; stronger heat rejection or a proven lower
power envelope is required. Root verified all 60 sealed file hashes and reran
the 12 whole-unit tests including the optional actual solver check.

| Work | Current independently checked result | Remaining work |
| --- | --- | --- |
| [E12-R2 ADC driver](../../electronics/adc_driver/revision2/README.md) | Separate fresh native run confirms 0 ERC, DRC, opens and parity issues. Both bias windows, supervisor, PD-level translation, shorter bypass/pump routes and separate force/sense terminals are implemented. Five conditional manufacturer-model cases rerun solver-clean. | Official ESS package/input data, final converter integration, analog partial-power isolation, actual coupled-loop/noise behavior, fabrication approval and all physical tests. |
| P03 complete replacement supply | Checkpoint `42addb43` has zero native ERC, all-severity DRC, schematic-parity and open-connection findings. The full pin contract, 12 buck EP vias and direct local bulk/HF links are checked. Old 5 V stages are replaced and retained bipolar sources are included. Nine current housing-integration cases clear after the local C300/R302 placement repairs. | Complete input-chain/startup margins, source/return interfaces, actual heat paths/uncertainty, .20 mm filled/capped via process approval and physical validation. Further thermal PCB repairs require renewed native closure and source-bound checks. |
| E28 disconnect | Corrected Q5B geometry, real return terminals and revised positive-5 V protection are being integrated; no closed-routing qualification is claimed. | Native routing, staged inrush/reverse-fault behavior, complete-terminal copper extraction, mechanical/process review and physical validation. |
| [E23I2 rear inlet](../../electronics/input_protection/inlet_revision2/README.md) | Five-component native schematic/PCB: 0 ERC, DRC, opens and parity findings; six independent physical copper connections. Four mutation tests reject broken/narrowed power copper or a missing logic via. | Mandatory rear fuse contract, complete adapter/connector/harness losses and fault coordination, assembly/process approval and powered tests. |
| [A12 integration](../../cad/a12/README.md) | Actual P03/E28 courtyards are now extracted on both populated faces. This caught the underside film capacitor and comparator-package problems, now repaired. The E28 mounting plane is raised to Z5.0; a nine-case full-board geometry check covers component-height/tolerance envelopes, all switch body/lead reserves and collision controls. A proposed individual-wire input crossover cleared five native geometry cases with explicit unapproved exit/position requirements. Separate checks cover the inlet, metal base, return hardware and lower-shell fasteners. | Refresh source-bound checks after final routing/bar regeneration; approve exact component/mate heights, input-wire exits/forming/retention, positive/protected-output harness routes and covers, fastener tolerances/engagement, structural/thermal behavior and all physical assembly checks. |

The completed stable review set currently has **82 passing tooling tests**. The standard-library-only run discovers the same 82, with four optional numeric checks skipped. Logs are in `generated/repair-tests-standard.txt` and `generated/repair-tests-portable.txt`. This count excludes unfinished P03/E28 repairs and is not a claim that the entire concurrently edited repository passes.

A separate [P03 ground-transfer investigation](../../qualification/boards/P03-GROUND.md) now uses actual finite barrels and distinct regulator/return electrodes. Three analytical numerical checks pass. The first unresolved snapshot is preserved. Actual ground-return repairs subsequently produced a numerical diagnostic matrix with 83 resolved electrodes at 0.1 mm, while one monitor return remained unresolved. This is not a certified resistance bound or complete endpoint-voltage pass; final native closure, material/manufacturing bounds, the signed current ledger and external-network coupling remain required.

The later P03 `a913baa` snapshot resolves all 84 noncapacitive ground electrodes on the 0.1 mm grid, including the monitor return; its archived matrix and current-balance checks supersede that earlier unresolved diagnostic for this copper. The 0.2 mm grid still misses U4.4. Different PGND-pin transfer coefficients require a real package-current split; no complete endpoint budget is claimed.

The [bipolar startup-ramp study](../../qualification/boards/BIPOLAR-SLEW.md) now distinguishes normal charging control from the higher fault-current limit, retaining a supported small-shunt comparison. It identifies late hard-off-bank closure as a way to defeat an upstream ramp and includes constant live-load pass energy. Three portable checks cover integrated energy, added capacitance and the earlier rejected shunt. This is an unimplemented architecture study; exact ramp/feedback, switching order, isolation, source capacity, SOA and physical validation remain open.

The historical E28 `b3be2731` native recheck has 50 open connections, zero hard DRC errors, zero ERC/parity findings and 79 retained DRC warnings (36 dangling tracks, 42 dangling vias, one sliver). The DRC artifact hash matches its receipt and the checked source remained unchanged during that check. This is progress from the earlier 123-open/three-hard-error snapshot, not native closure or fabrication approval. The main A12 nine/five-case receipt below still belongs to the explicitly named earlier E28 input and requires renewal for subsequent revisions.

The earlier E28 `7b5227fd` checkpoint has 46 opens, zero hard DRC/ERC/parity findings and 76 retained warnings, bound by `native-force-safe-promoted1.json`. A 36-open intermediate was rejected because its routing cuts damaged force copper and failed the voltage-drop allocation; that failed evidence remains archived. Connectivity improvement cannot waive conductor/return-network requirements. The [isolated routing pilot](../../qualification/boards/FREEROUTING-PILOT.md) preserves a validated unchanged native roundtrip and separately rejected imports. Its experiments did not promote a board or establish copper closure.

The later current E28 `2830c887` checkpoint closes the C40 bypass-ground
connection using three actual front-layer tracks, with no moved parts or added
drills. Root independently checked its complete native source hash map and raw
report: **45 opens, zero hard DRC/ERC/parity findings and 76 dangling warnings**.
An independent normalized KiCad comparison confirms complete footprint/pad,
edge, zone-contract and board-setup equality with `7b5227fd`. The routing change
removes 0.91148 mm² of P12_SRC fill; the finite 0.5051 mΩ diagnostic penalty is
retained, not waived. Actual conductor/return, startup and physical qualification
remain open; the improvement is one repaired native connection.

The [SC01 positive startup draft](../../qualification/boards/startup_circuit/README.md) now supplies an actual separate 56-component native schematic, zero ERC errors, six unresolved footprint warnings and nine passing pin/topology/integrity tests. It exposes the 2.5 V protection-output versus 3.3 V enable-input mismatch. PCB implementation, sequencer/translator integration and physical validation remain unfinished; its conservative +19 V ramp misses the provisional five-second target. It does not complete the existing bipolar-startup hold.

The separate [SC02 negative draft](../../qualification/boards/startup_circuit_negative/README.md) has 60 parts, zero ERC errors, eight declared footprint warnings and nine passing integrity tests. It identifies concrete negative-controller headroom, gate-injection and timing failures; it is not an approved counterpart. The [NF01 comparison](../../qualification/boards/startup_negative_feasibility/README.md) identifies native soft-start using LTC4252A as a more plausible next architecture, with eight calculation/mutation checks. Its missing guaranteed transfer/timing and fault-energy bounds remain explicit, and no controller change is implemented in the operating boards.

The [protected-output escape study](../../cad/a12/harness/README.md) is rejected: its selected AWG14 curves clear the declared electronics and one another but collide with the control mechanism and power-link/return hardware. Thin-insulation and controlled 3D alternatives also fail native collision checks. A copied J4/PCB-extension proposal has zero hard native/ERC/parity findings but 47 opens; its new solder-joint reserve intersects a return retainer. An actual offset-head retainer prototype clears the components but collides with a return-bar corner and the positive-link support. Both proposals remain separate and rejected, with source-bound native evidence. Local component/board MCAD checks therefore cannot establish complete harness fit. Actual terminations, routing, support and bend/assembly checks still need repair.

The shared A12 height resolver now uses the exact selected TDK 0402/0805 requirements before generic package allocations, including 0.65/1.55 mm assembled projections. Five projection/intersection regression tests pass. Fresh nine-case board and five-case input-wire native checks clear on P03 `a913baa` / E28 `740d39ec`, including all 29 switch reserves and 14 mounting-head requirements. Later PCB changes require refreshed bindings. The separate [positive-link prototype](../../cad/a12/positive_links/README.md) provides copper shapes, captured covers and a support candidate with archived checks; complete link resistance, insulation, support strength, lifetime and physical fit remain unqualified. These additional results do not change the earlier 82-test review set into a whole-repository test claim.

A later complete renewal now clears the same nine body/board/control and five
input-wire native cases on closed P03 `42addb43` / E28 `7b5227fd`, with 506 native
electrical parts. Root independently verified the P03 source/artifact hash maps
and raw zero ERC/DRC/parity/open findings. The 67 bound geometry inputs, receipts,
logs and STL artifacts are captured in
`hardware/cad/a12/generated/history/board-input-capture-16f8ea8d88e80e38.tar.gz`
with a hash manifest. This is the current body/input-wire checkpoint, not a
complete output-harness, thermal or physical-fit acceptance. Future thermal or
terminal repairs require another source-bound review.

A separate 54 mm-shell study clears nine local protected-output geometry cases,
but the complete connection to the present E19 input reserve needs at least
183.20/186.09 mm of wire, exceeding the selected 150 mm limit even before final
terminations and slack. The height choice has not been adopted. A native outer
envelope audit also corrects the earlier 66.8 mm description: that dimension
ends at the shell. Knobs/control travel and thermal feet bring nominal overall
height to 87.6 mm with the existing 38 mm shell, or 103.6 mm for the taller study.

The [stronger U10 thermal draft](../../cad/a12/thermal/candidates/u10_stronger/README.md)
reclaims actual matching bottom copper and uses eight direct EP barrels. With
the same stated material/gap/thickness scenarios, its sensitivity result is
95.39 °C at an assumed 60 °C base. Seven native geometry cases pass and root
independently checked all 58 sealed source/evidence hashes. It remains an
electrically incomplete draft with 19 opens and unbounded package/material/
contact/whole-path uncertainties. The whole-base 60/65 °C conditions are not
proven upper bounds: the 10.5578 W provision covers supply loss, while downstream
processor/LED/analog heat and actual enclosure-to-base heat sharing are not yet
bounded. Neither that ledger nor a local thermal scenario qualifies the full unit.

The subsequent restored U10 source `f94c8005` and U102 source `138931e3` are
electrically closed: root independently checked their raw zero ERC/DRC/parity/
open findings and all native source/artifact hash maps. Each also clears nine
actual board/body/control/case cases, with fresh actual PCB poses, both faces
and all 506 electrical parts, against E28 `2830c887`. Receipts are in
`hardware/cad/a12/generated/candidate-fit/`. New thermal contact pieces, complete
power links, wiring, thermal/quiet-ground extraction and physical qualification
are separate requirements; neither candidate is promoted to the operating board.

A primary-layout audit adds a concrete AUX stability repair: U102 is on F.Cu,
but required VIN_IC input bypass C102 and main output C106 are on B.Cu.
Front-side C107 is only 100 nF; the regulator delay capacitor C110 is also B.Cu
and needs a local-ground/layout review. C104 is on VIN_PROTECTED and C105 on
INPUT_SLEW, so neither supplies the direct VIN_IC bypass. TI specifies at least
0.1 µF input/2.2 µF output capacitance and directs local regulator capacitors
onto the regulator's own PCB face, with a direct output-cap ground return.
[TPS7A16 Rev F, sections 8.2.1.2.1.3 and 10.1](https://www.ti.com/lit/ds/symlink/tps7a16.pdf).
Actual effective capacitance, same-face placement/ground, restored local loops,
native closure and stability checks must precede adoption. Remote AUX-load
bypasses have separate roles and are not automatically regulator-local parts.

The separate repaired AUX front-cell candidate `37fd6109` now places the actual
input bypass C113, main output C106 and delay C110 on F.Cu with U102. The native
source is electrically closed; six bounded direct front-copper paths are
recorded rather than treating a long connected detour as an acceptable local
loop. Its fresh nine-case body/control/housing check uses all 507 actual parts
and exact selected capacitor projections (2.9/1.60/1.0 mm). No checked
intersection or same-board body/lead overlap remains in that scope. The source,
raw native reports and exact mechanical evidence are captured in the
`aux-front-body-checks-c02fbcd1e9c7b3b4` manifest under `hardware/cad/a12/generated/history/`.
Effective capacitance/ESR over bias, temperature and life, regulator stability,
actual thermal paths, complete links/wiring and physical qualification remain
open; this candidate has not replaced canonical P03 `42addb43`.

The separate E28 R58-only source `fed47258` repairs an actual output-joint
clearance conflict by moving R58 0.2 mm, retaining its native pad/barrel contacts
and all other copper, holes, footprints and J4 geometry. Its 45 routing opens
remain; raw ERC/hard DRC/parity are zero. With the explicitly separate AWG18
`balanced-return` wire proposal, all 14 local native source/wire/joint/pair/
hardware/case checks clear in the existing 38 mm shell. This is captured by
`hardware/cad/a12/harness/generated/formed-6715-r58-local-clear-77bc675f1bdb193a.json`.
The original E19 receiving header has 1 mm holes versus the proposed wire's
1.2192 mm nominal core: receiving termination, complete route/fanout, actual
assembled loss, current/temperature and strain qualification remain unfinished.
Neither the R58 source nor the wire proposal is adopted into the canonical BOM.

The separate fresh ADC native evidence is in `generated/r2-independent/`; the separate five-scenario rerun is in `generated/r2-spice-independent/`. The agent's original handoff receipts remain unchanged. These simulations exclude the complete servo/reference/pump, actual switched ADC input and extracted board parasitics. A clean solver result does not establish phase margin or physical audio performance.

A separate [coupled ADC investigation](../../qualification/boards/COUPLED-ADC.md) now includes the actual left input buffer, reference buffer and common-mode servo using three unmodified TI libraries. All five initial runs require solver assistance and are rejected for numerical comparison; they do not extend the earlier clean stage-only result into a full-board pass. The complete-load, clamp/pump/PD, parasitic and physical stability gates remain open.

The [ESS request draft](vendor-data-request.md) identifies the missing package and interface data and a proposed authorized-distributor contact. It has not been sent. No datasheet access, manufacturer approval, purchased sample, assembled board, calibrated instrument or physical measurement is inferred from a draft or a software result.
