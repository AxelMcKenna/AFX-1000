# Standalone fabrication preparation

**The complete unit is not ready for fabrication.** This inventory targets the
first prototype of the full 12 V higher-headroom standalone design. B1 is separate.

The [current AUX load review](staging/two-board-aux-load-review-01/README.md)
finds that the old AX03 current budget cannot transfer unchanged to TBP25:
E_U42 now uses LVC with three active inputs, and POWER_READY has two loaded
enable branches. The current rail inventory contains 81 IC supply pins and
28.4 µF of direct nominal capacitance in that snapshot; TBP31 below adds
0.1 µF for the comparator. Conditional current and thermal screens
identify the requirements to resolve before accepting AUX distribution;
they do not establish actual current or thermal limits. The subsequent routing
revision below preserves the circuit and corrects the stale E_U42 datasheet link.

These are 15 functional roles, not a decision to manufacture 15 separate PCBs.
The final physical partition and integrated assembly remain unfinished.

The [current housing/consolidation review](staging/housing-consolidation-review-01/README.md)
checks all eight latest main-board outlines and the declared audio/digital/monitor
receivers. A 268 × 63 mm combined signal-board proposal passes the limited common
height screen; eight main boards are not established as necessary. Complete
component, support, harness and native assembly fit remains unverified. This
earlier outline study is followed by the two-board candidates below.

The [two-main-board placement candidate](staging/two-board-review-01/README.md)
now places all 1,543 known electrical parts on a 268 × 63 mm signal board and
a connected 320 × 181.1 mm power/protection board. Both bundled KiCad projects
pass native placement geometry/library checks with no ignored categories.
The missing codec, complete routing, current thermal/support hardware and full
installed-fit checks remain unfinished. Integrated schematics now follow below. The existing selected
boards remain reference checkpoints; the new placement is not a fab release.

The newer [integrated signal-main checkpoint](staging/two-board-signal-routed-native-03/README.md)
retains Daisy Seed 3, joins 19 scheduled header-pin pairs into 16 shared nets,
and restores 5,767 source segments and 917 vias. All 467 schematic components,
1,680 pin entries and 676 original physical connection groups are checked.
It has **251 opens, zero geometry/ERC findings and one missing codec footprint**.
The [power interface reconciliation](staging/two-board-power-interface-audit-01/README.md)
checks 30 proposed pin pairs and identifies legacy protection-bypass hazards;
its findings feed the integrated power schematic below. Remaining loaded
electrical checks and mechanical release work are unfinished.

The [inlet copper resistance screen](staging/two-board-inlet-resistance-02/README.md)
uses TBP35's actual filled copper and contacts across nine sections. Under an
assumed 4 A load and uniform 85 °C copper temperature, the modeled copper
subtotal is **186.6 mV/0.747 W at 35 µm**, or **93.3 mV/0.373 W at 70 µm**.
All nine sections pass numerical refinement/shift checks within 1.332%, with
analytical/topology tests and independent conservation/arithmetic review.
Ideal-port currents show that transition vias cannot be assumed to share
current evenly. Via barrels, component/contact losses and local bulk return
are excluded; this is not a complete input-loop model, accepted stack or
thermal/current rating. That analysis did not edit the PCB; the newer routing checkpoint below changes the distribution and slightly refills the inlet plane.

The [current power checkpoint](staging/two-board-power-startup-remaining-native-03/README.md)
closes **27 connections**, completing the remaining eight U18–U28 local
bypass/ground cells and U19's additional supply-pin tie. All eleven local
cells are complete, but none reaches the AUX regulator source yet.
**2,172 power opens remain**. Native geometry/parity/ERC errors are zero,
with two retained isolated-reference warnings.

All **1,555 retained reference cases**, 18 new paths and nine previous
startup-repair paths pass. Three reference regressions found in rejected
candidates are repaired by accounting for native plane minimum thickness.
All eleven supply-plane fields and seven quiet-ground fields remain exact.
All seven quiet networks preserve connected ownership and pin-8-only stars.
An existing unanchored ground fragment is excluded from reference coverage
and remains unchanged.

Current copper has 3,012 tracks, 482 vias, 47 zones and 2,910 native connection
groups. Five capacitors move; six In6 detours and a U20 front enable bridge
preserve local route references. The pass adds 69 tracks and 20 vias, retires
112 tracks, extends one main In6 ground outline and refills four main-ground
zones. The other 43 fills and all other outlines remain exact. Earlier inlet
resistance/current-sharing results remain historical.

[Status-50](staging/two-board-fabrication-status-50/status.json) records the
selected projects and checked evidence. Thirteen current copper views were
directly inspected. The
[startup-net survey](staging/two-board-startup-connectivity-survey-06/README.md)
identifies **58 missing joins across 32 of 91 surveyed nets**. The
[cell survey](staging/two-board-startup-cell-survey-04/README.md) confirms local
bypass/ground completion for U18–U28, with missing auxiliary source links.
The [AUX inventory](staging/two-board-aux-distribution-survey-02/README.md)
records **eight of 81 IC supply pins connected to the regulator, 73 unconnected**
and 28.5 µF nominal direct capacitance. Current, effective capacitance, startup
and installed thermal limits remain unresolved. Local bypass completion does
not establish powered or functional startup circuits.

Startup/fault behavior, protected outputs, analog/module distribution, source/
input loops, force/quiet returns and signal routing remain unfinished.
Whole-unit electrical/thermal, installed-fit, accepted manufacturing stack/BOM,
approved ESS package inputs, fabrication outputs and prototype bring-up work
are still required. **This is not a fabrication release.**

The [previous digital-return checkpoint](staging/two-board-power-digital-return-native-03/README.md)
completed R104's quiet-ground return beside U15 and repaired the adjacent
master-enable route, closing one connection from TBP45. Those changes remain
in the current board.

The [previous analog checkpoint](staging/two-board-power-analog-cells-native-03/README.md)
completed 26 local control and quiet-return joins across U13/U14/U32. Its
placement and circuit changes remain in the current board; its recorded
counts and per-pass measurements apply to TBP45.

The [previous permission checkpoint](staging/two-board-power-permission-native-04/README.md)
moves U42 with C85 and completes 25 targeted permission, follower, pull-up and
NF header interconnects. Including local bypass and main-ground joins, this
closes **30 native connections**, leaving **2,237 power opens**. Seven targeted
control nets are fully connected, including ALL_RAILS_ALLOW and both NF header
signals. All seven PG pull-up AUX ends join the existing supply group.

Native geometry/parity/ERC errors are zero, with two retained isolated-reference
warnings. The board retains 1,101 footprints, 1,086 electrical parts and 3,420
schematic pin entries. Two footprints and ten pads move. Current copper has
3,039 tracks, 435 vias, 39 zones and 2,975 native connection groups. This pass
adds 183 tracks and 49 vias, replaces one ANA_PG0 segment, extends four main-ground
outlines and refills eleven fields while retaining twenty-eight fills exactly.

All **72 new or replacement route sections** have adjacent ground projection
with recorded same-net via and plated-pad antipad exclusions. The independent
audit proves every declared merge and preserves all other connections, 1,015
complete prior reference cases, 22 own-quiet support sections, four star-only
eFuse returns and all 33 fast-OV sections. All 70 TBP43 sections are rechecked,
including the restored ANA_PG0 detour. In4 source copper remains one connected
834.498043 mm² field with 20 contacts. Its 1.712206 mm² fill change is explained
by declared vias and a separately verified native single-via control. In5
uncovered source projection is 0.349983 mm². Earlier support coverage remains
24/28 and TBP40 startup coverage remains 7/15; those gaps remain unfinished.

[Status-44](staging/two-board-fabrication-status-44/status.json) verifies 977
direct bindings. Nineteen current views were directly inspected. The
[previous startup-routing checkpoint](staging/two-board-power-startup-completion-native-06/README.md)
records TBP43's U30/U34/U41 interconnect and reference work.

Next work is pulldown returns and full startup review, retained reference gaps,
protected outputs, analog/module distribution, force/quiet returns and signal
routing. Load/fault/thermal qualification, approved ESS inputs, accepted stack,
exact BOM, complete installed fit, manufacturing outputs and prototype bring-up
planning remain required. **This is not a fabrication release.**

The [previous startup-logic checkpoint](staging/two-board-power-startup-logic-native-02/README.md)
moves U29/U40 with their existing bypass capacitors, restores U29's two
master-enable connections, and closes **sixteen native connections** across
PG/Schmitt/follower logic, AUX branches, bypass supplies and main returns.
**2,294 power opens remain**; signal remains at 251 plus the missing ESS.
Four parts move without changing circuit values, packages or pin assignments.

The first candidate was rejected despite zero geometry/parity errors: new In6
routes split U17's quiet return and disconnected C47/R112. Revised surface-to-
inner transitions restore all prior connectivity and all four star-only quiet
returns. Native geometry/parity/ERC errors are zero, with two retained warnings.
The independent audit preserves 299 prior complete ground projections, all
22 own-field support screens and all 33 fast-OV reference sections.

Current copper has 2,683 tracks, 338 vias and 36 zones. One In5 return outline
extends to the logic; seven fills change and 29 remain exact. The source field
keeps all 20 contacts and 836.210216 mm² of copper; its uncovered In5 projection
remains 0.355273 mm². Only **2/32 new logic sections** have full adjacent-ground
coverage. Retained support is 24/28 and retained TBP40 startup coverage is 6/15.
[Status-41](staging/two-board-fabrication-status-41/status.json) verifies 875
direct bindings; eleven current views are inspected. Complete the new reference
paths, U29 ALL_RAILS_ALLOW, remaining U30/U34/U41 logic/supplies/bypass and pull-up
AUX ends, then protected outputs and remaining routing. Accepted stack/current/
thermal limits, ESS inputs, full installed fit and reviewed manufacturing outputs
remain required. **Not a fab release.**

The [previous startup checkpoint](staging/two-board-power-digital-startup-native-02/README.md)
connects four supply-good pull-ups and three follower-enable pull-downs, closing
**ten native connections**. **2,310 power opens remain**; signal remains at
251 plus the missing ESS footprint. Seven resistors move on the bottom side.
The U17 star moves 0.25 mm, C47 gets a 1.600 mm local quiet return, and R112
gets a 1.077 mm return to its own quiet field. All four star-only connections,
the earlier master-enable group and all other previous connections survive.

Native geometry/parity/ERC errors are zero, with two retained warnings.
Independent review verifies all circuit parts and pins, the seven rigid moves,
exactly ten joins, 274 earlier complete ground projections and 22 own-field
support screens. All 33 fast-OV reference sections remain complete. Current
copper has 2,602 tracks, 316 vias and 36 zones; 21 fills remain exact and 15
are refilled. Retired-via holes are restored in In5; the source-plane reference
screen leaves 0.355273 mm² uncovered. Only 7/16 new startup route sections have
full adjacent-ground projection. [Status-40](staging/two-board-fabrication-status-40/status.json)
verifies 1,351 direct bindings, and nine current views are checked. Finish the
Schmitt/gated startup chain, pull-up AUX supplies, bypass and reference paths,
protected outputs and remaining routing, accepted stack/current/thermal limits,
ESS package, full installed fit and manufacturing outputs. **Not a fab release.**

The [previous reference-plane checkpoint](staging/two-board-power-digital-reference-native-02/README.md)
adds dedicated In1/In6 quiet-ground references for all four digital eFuse cells.
The source plane moves from In6 to In4, retaining all 20 contacts and its In5
return reference. A six-segment DVDT reroute now stays over its own quiet field.
**2,320 power opens remain**; signal remains at 251 plus the missing ESS.
All 3,058 earlier connected groups, 1,101 footprints and 3,420 circuit pin
assignments are preserved. Geometry/parity/ERC errors are zero, with two retained
reference warnings. Twenty-four earlier zone records remain exact; five ground
outlines change, one source zone changes layer and six ground zones are added.
All 234 earlier complete ground projections and 33 fast-OV sections retain
reference. Ground coverage improves from 2/28 to 24/28 full route screens; the
remaining summed 0.001294 mm² lies beside same-signal vias and remains reported.
[Status-39](staging/two-board-fabrication-status-39/status.json) verifies 1,300
direct bindings and nine current views are inspected. Quiet-return lengths and
parasitics, output/startup routing, remaining routing/distribution, stack/current/
thermal limits, approved ESS package, full fit and manufacturing outputs remain
unfinished. **This is not a fabrication release.**

The [previous support-cell checkpoint](staging/two-board-power-digital-cells-native-03/README.md)
connects the four digital eFuse current-limit and slew-rate networks and eight
quiet returns, closing 20 connections. **2,320 power opens remain**; signal
remains at 251 with its ESS footprint missing. Fifteen passives move, including
five side changes; values and circuit pin assignments remain unchanged.
All 3,078 earlier connected groups survive. Native geometry/parity/ERC errors
are zero, with two retained isolated-reference warnings. All 308 via drills
pass the SMD-land screen, with a 0.163872 mm minimum gap. All 233 earlier
complete adjacent-ground projections and 33 fast-OV sections retain reference.
Twenty existing fills remain exact; ten fills and six outlines change.
[Status-38](staging/two-board-fabrication-status-38/status.json) verifies 834
direct bindings; eight current views are inspected. New support-route ground
coverage, parasitics and longer quiet returns still need work. Finish protected
outputs/startup controls, remaining routing/distribution, accepted stack/current
and thermal limits, approved ESS package inputs, full installed fit and
manufacturing outputs. **This is not a fabrication release.**

The [previous digital-source checkpoint](staging/two-board-power-digital-distribution-native-02/README.md)
connects U20's output to four digital eFuse input pairs, four input capacitors
and E_J11, closing 29 connections. **2,340 power opens remain**; signal remains
at 251. Forty-seven tracks, 38 vias and six zones provide the source plane,
force-return extension and four separate quiet-ground islands. Each island
has a single plane connection through its device GND-pin via. Input and
protected-output nets stay separate. All 3,107 previous physical connection
groups, all component geometry and circuit pin assignments are preserved.
Native geometry/parity/ERC errors are zero, with two isolated-reference warnings.
All 300 via drills pass the SMD-land screen, with a 0.163872 mm minimum gap.
Twenty earlier fills remain exact; four inlet planes refill and two ground
outlines gain quiet-via exclusions. All 229 previously complete adjacent-ground
track projections and all 33 fast-OV route sections retain their reference.
New source-plane In5 coverage is about 99.9592% after contact exclusions;
0.331629 mm² remains uncovered at 17 via/hole boundary regions. This is not
complete reference or current/thermal qualification. [Status-37](staging/two-board-fabrication-status-37/status.json)
verifies 843 direct bindings; 12 current views are inspected. Finish eFuse
output/support routing and local bypass placement, remaining distribution,
accepted stack/current sizing, full installed fit and manufacturing outputs.

The [previous regulator-feed checkpoint](staging/two-board-power-regulator-distribution-native-04/README.md)
connects both main regulator input cells to the protected supply and joins the
analog regulator return. **2,369 power opens remain**, three fewer than TBP35;
signal remains at 251. One In2 feed zone and two In1 ground bridges use existing
vias and local In3 planes. All components, tracks, vias, circuit values and pin
assignments are preserved. Native geometry/parity/ERC errors are zero, with
the same two isolated-reference warnings. The independent review preserves all
3,110 prior connection groups and all 228 previously complete adjacent-ground
track projections. All 33 full fast-OV route reference screens pass.
New-feed reference coverage is 99.9936% after supply-contact exclusions;
eight small via-bank/header-reserve regions total 0.043961 mm², so full area
coverage is not claimed. [Status-36](staging/two-board-fabrication-status-36/status.json)
verifies 824 direct bindings, and nine current views are inspected. Actual
current sharing, complete-loop resistance, thermal/noise behavior, remaining
distribution/routing and full installed fit still need work.

The [previous fuse checkpoint](staging/two-board-power-inlet-fuse-native-01/README.md)
corrects I_F1 from the unsupported `0451006.MRL 6A 125V` to the manufacturer-listed
**045106.3MRL, 6.3 A, 125 V**. The schematic, symbol library, board properties and
circuit contract agree. An independent whole-board comparison and native capture
prove all copper, 21 zones, 3,110 connection groups and 3,420 pin-net entries
unchanged. The existing nominal lands match the series drawing and the package
fits the prior body/height allocation. This does not qualify complete installed
fit. **2,372 power opens and 251 signal opens remain**; native power
geometry/parity/ERC errors remain zero, with two reference warnings.
[Status-35](staging/two-board-fabrication-status-35/status.json) verifies 975 direct
bindings. TBP34's inspected copper exports remain applicable through exact
geometry comparison. The [fuse review](parts/inlet-fuse-01/README.md) records
conditional loss and derating calculations; hot resistance, startup and
adapter/TVS/jack/copper fault coordination remain unqualified.

The [previous input-TVS checkpoint](staging/two-board-power-input-tvs-native-01/README.md)
moves D101 beside the input MOSFET and connects its source and return through
broad back copper, closing two connections. **2,372 opens remain**; all ten
pads on the fused DC-input net now connect. Native geometry/parity/ERC errors
are zero, with two isolated-reference warnings. All 3,112 earlier connection
groups remain intact; 1,100 complete footprints stay unchanged and D101's two
moved pads are independently verified. All 228 previously complete full-width
adjacent-ground projection cases pass, as do all 33 current fast-OV route
projections. The separate AUX return is preserved. All 262 via drills pass
the SMD-land check. [Status-34](staging/two-board-fabrication-status-34/status.json)
verifies 674 direct bindings and 11 visual views are reviewed. TVS surge,
temperature, fuse coordination, complete power-path current/thermal limits,
remaining routing and installed fit remain unqualified.

The [previous inlet checkpoint](staging/two-board-power-inlet-corridor-native-02/README.md)
connects the fused inlet and return through paired internal planes, closing
nine connections: **2,374 opens remain**, with zero native geometry/parity/ERC
errors and two isolated-reference warnings. All 3,121 previous connection
groups and 1,101 complete footprints remain unchanged. All 33 fast-OV route
sections retain adjacent ground coverage, and the AUX return remains separate.
The four new internal planes use nominal 0.51 mm mounting-hole edge clearance,
increasing H_NEW2 copper width from 1.16 to 5.56 mm per layer while retaining
surface fastener reserves. Nineteen zones include one split In5 region;
every new filled piece contacts its intended native group. All 250 via drills
pass the SMD-land check. [Status-33](staging/two-board-fabrication-status-33/status.json)
verifies 707 direct bindings; 20 visual views are reviewed. The input TVS,
full distribution/return routing, current sharing, thermal/transient behavior,
accepted stack and complete installed fit remain unfinished.

The [previous power checkpoint](staging/two-board-power-fast-ov-return-native-02/README.md)
shortens Q103's gate connection and corrects the fast-OV ground-reference
gaps. All 33 current route sections have adjacent ground coverage, excluding
their own signal-via antipads. **2,383 opens remain**, unchanged this pass,
with zero native geometry/parity/ERC errors and two retained isolated-reference
warnings. All 3,121 prior connection groups and AUX split-return topology
are preserved. All 14 regions remain contiguous; nine fills remain exact.
Independent checks verify five moved pads, every copper change, placement
and all 234 via drills. [Status-32](staging/two-board-fabrication-status-32/status.json)
verifies 709 direct bindings. Full current/thermal and cutoff behavior,
source/return distribution, remaining routing and manufacturing/installed-fit
work remain unfinished.

The [previous fast-OV circuit checkpoint](staging/two-board-power-fast-ov-native-03/README.md)
connected the fast-OV circuit, VIN-to-AUX link and C102 ground, closing 22
connections. Its added comparator bypass brings the AUX direct nominal
capacitance to 28.5 µF. TBP32 above preserves its circuit and corrects its
recorded geometric reference gaps; loaded startup and effective capacitance
remain unqualified.

The [previous input-threshold checkpoint](staging/two-board-power-input-thresholds-native-03/README.md)
connects the local UV/OV dividers, clamp and AUX bias branches, closing
15 connections. Seven resistor footprints move, including three to the back.
A new In6 ground region covers the full-width projections of 16 checked
back-side routes except for their own signal-via antipads. **2,405 opens
remain**, with zero native geometry/parity/ERC errors and two retained
isolated-reference warnings. All 3,158 prior connection groups are preserved;
all 14 regions are contiguous. The independent audit checks moved pads,
retained copper, fill changes, placement and all 219 via drills. AUX return
topology remains intact. [Status-30](staging/two-board-fabrication-status-30/status.json)
verifies 707 direct bindings. Complete source/return distribution, fast
OV monitoring, electrical qualification, remaining routing, manufacturing
requirements and installed fit remain unfinished.

The [previous input-bypass checkpoint](staging/two-board-power-input-bypass-native-03/README.md)
connects the IN_SYS bypass behind U101 and its local PGTH divider, closing
seven connections. Four footprints move, including C101 to the back;
five PG tracks and one via are replaced by local escapes and In3 branches.
**2,420 opens remain**, with zero native geometry/parity/ERC errors and two
retained isolated-reference warnings. All 3,165 earlier connection groups,
retained copper and seven previous fills remain intact. All 13 native
regions are contiguous, six regions refill without outline or setting changes,
and the AUX return topology and existing control/output references pass.
Independent checks verify all eight changed pads and all 207 through vias.
[Status-29](staging/two-board-fabrication-status-29/status.json) verifies 683
direct bindings. UV/OV and clamp routing, complete bypass/reference qualification,
source distribution and full fabrication/installed-fit work remain unfinished.

The [previous blocking-FET checkpoint](staging/two-board-power-input-source-native-03/README.md)
groups the blocking FET/pulldown pair, connects both input pins and routes
the output capacitors with a 2 mm front bus and expanded In1 return/reference.
Five footprints move, including C104 to the back using the identical C102
package. Twenty-four tracks and six vias are added; three PG tracks are
explicitly replaced. **2,427 opens remain**, with zero native geometry/parity/
ERC errors and two isolated-reference warnings. Independent checks preserve
all 3,178 previous connection groups and every retained track/via, verify
all 27 changed pad instances and seven unchanged earlier regions, and prove
all 13 filled regions contiguous. AUX return topology and control/output
reference coverage pass. The native exporter removes 24,955 duplicate symbol
paths with no copper or circuit change. [Status-28](staging/two-board-fabrication-status-28/status.json)
verifies 679 direct bindings. Input bypass/thresholds, full source and return,
actual stack/current/thermal/transient limits, all remaining routing and full
manufacturing/installed-fit work remain unfinished.

The [previous input-control checkpoint](staging/two-board-power-input-controls-native-02/README.md)
places C105/R107 beside the input eFuse and connects dVdT, ILIM and their
local ground returns. Thirteen tracks, two through vias and two local
F/In1 ground regions close five connections. **2,440 opens remain**, with
zero native geometry/parity/ERC errors and two isolated-reference warnings.
All 3,183 prior connection groups, old tracks/vias and eight existing zone
outlines/fills are preserved. The full control-trace projection has In1
reference; only four pads on the two moved front passives change. Native
refill, independent electrical/placement checks and layer review pass.
[Status-27](staging/two-board-fabrication-status-27/status.json) verifies 668
direct bindings. Input force paths, voltage dividers, bypass placement,
exact passive tolerance/startup/thermal requirements and full fabrication
and installed-fit work remain unfinished.

The [previous AUX PG checkpoint](staging/two-board-power-aux-pg-native-01/README.md)
connects AUX PG to the input eFuse SHDN pin and C102 to the local AUX VIN cell.
A 0.361 mm feedback-via relocation and three renewed tracks make room for the
PG escape. All 3,185 prior connection groups remain intact; all component
poses, values, lands and pin/net assignments are unchanged. Native checks show
**2,445 opens and zero geometry/parity/ERC errors**, with the two retained
isolated-reference warnings. Three AUX ground fills are renewed, the other
five remain exact, and split-return topology and FB reference coverage pass
independent checks. E_U42's datasheet metadata is corrected to the selected
LVC device. [Status-26](staging/two-board-fabrication-status-26/status.json)
records the selected project, 661 checked direct bindings and remaining work.
The complete VIN source, AUX distribution, RUN net and electrical/thermal
requirements remain unfinished.

The [previous AUX ground checkpoint](staging/two-board-power-aux-ground-native-02/README.md)
adds separate front AUX input/output returns, back feedback-ground copper,
an In1 thermal/reference region and four conventional thermal vias. Four short
front straps connect the exposed-pad copper. All **2,447 opens** are retained;
this improves return topology without claiming new connectivity. Native
geometry/parity/ERC errors remain zero, with two isolated-reference warnings.
The multilayer cut check proves that input and output returns separate when
only U102's ground-pin land is removed. The full FB trace projection has In1
reference except its own via antipads. A small U20 edge recess provides room;
all 12 U20 ground-via contacts and its sense reference are preserved. All 3,185
previous groups, ordinary copper and component geometry remain intact. The
other three old zones/fills are unchanged. [Status-25](staging/two-board-fabrication-status-25/status.json)
verifies 647 direct bindings. AUX source/output/PG routing, load, capacitor
and thermal review, wider distribution, manufacturing and installed fit remain.

The [preceding AUX local-routing checkpoint](staging/two-board-power-aux-local-native-01/README.md)
groups and locally routes the AUX regulator, four capacitors and three feedback
resistors. Eight footprints move, with no changes to their values, packages or
sides. Thirty-two tracks and five vias close 15 connections, leaving **2,447 opens**.
Native geometry/parity/ERC errors remain zero, with two isolated-reference
warnings. All 3,200 earlier connection groups, all old tracks/vias and all four
zone outlines/fills are preserved; fresh refill independently confirms the
unchanged planes. The regulator and capacitors remain on the front, with short
input/output/delay paths. All 186 vias pass the drill-to-SMD clearance check.
[Status-24](staging/two-board-fabrication-status-24/status.json) verifies 656 direct
bindings. AUX ground regions/thermal vias, source/output/PG distribution,
load/derating/startup/thermal review and full fabrication/installed-fit work remain.

The [preceding U23 quiet-return checkpoint](staging/two-board-power-u23-quiet-native-01/README.md)
recesses U23's In1 force plane around the remote MODE return, so its quiet link
enters near BP5. One short front track and one additional return via preserve
all 3,200 earlier groups and **2,462 opens**. Native geometry/parity/ERC errors
remain zero, with two isolated-reference warnings. The other three planes and
all old ordinary copper/component geometry stay unchanged. The recessed U23
plane remains contiguous, and its sense trace retains full projected reference
coverage apart from its own via clearances. [Status-23](staging/two-board-fabrication-status-23/status.json)
verifies 657 direct bindings. A [screened AUX cell](staging/two-board-aux-cell-survey-01/README.md)
now supplies a concrete seven-move/eight-part placement candidate; it is not yet
implemented or natively checked. Full electrical, routing, manufacturing and
installed-fit requirements remain open.

The [preceding U20 input checkpoint](staging/two-board-power-u20-input-native-01/README.md)
connects both U20 VIN/PGND branches, both bulk input capacitors and the BP5 quiet
return through two new local planes. C204 moves to the back beside the left
input branch; its value/package and all earlier tracks/vias stay unchanged.
Sixteen tracks and thirteen vias close seven connections, leaving **2,462 opens**.
Native geometry/parity/ERC errors are zero, with two retained isolated-reference
warnings. All 3,207 earlier groups and both U23 zones/fills are preserved. The
new In1 ground and In3 input planes are each contiguous; the ground plane covers
the full 0.2 mm sense-trace projection except its own via clearances. A recess
keeps the remote configuration return outside the force plane until near BP5.
[Status-22](staging/two-board-fabrication-status-22/status.json) verifies 652 direct
bindings. Actual capacitor derating, current/thermal/stability, enable reference,
wider distribution, AUX/other cells and full fabrication/installed-fit work remain.

The [preceding U20 enable checkpoint](staging/two-board-power-u20-enable-native-01/README.md)
connects U20 EN, R204's existing feed and R205's pull-down/quiet return. Six route
sections add eight tracks and three vias, closing three connections with
**2,469 opens** remaining. Native geometry/parity/ERC errors are zero; two
isolated-reference warnings remain. All 3,210 earlier physical groups, component
poses, old copper and both U23 planes are preserved. All 167 vias pass the
0.165 mm minimum drill-to-SMD gap. The In4 feed clears the intervening mounting
reserve; its reference environment and full enable behavior remain unqualified.
[Status-21](staging/two-board-fabrication-status-21/status.json) verifies 389 direct
bindings. U20 input and quiet/force/reference planes, wider board routing,
remaining circuit qualification and full manufacturing/installed-fit work remain.

The [preceding U20 control checkpoint](staging/two-board-power-u20-control-native-01/README.md)
connects U20 output sense, feedback trim and FSEL/MODE configuration. Thirteen
route sections add 16 tracks and seven vias, closing six connections with
**2,472 opens** remaining. Native geometry/parity/ERC errors are zero; two
isolated-reference warnings remain. All 3,216 earlier groups, existing copper,
component placements and both U23 local planes are preserved. The dedicated
In2 sense path has 1.15 mm minimum projected separation from switching copper;
its reference plane and quiet-ground-to-PGND connection remain unfinished.
[Status-20](staging/two-board-fabrication-status-20/status.json) verifies 389 direct
bindings. The [capacitor review](staging/two-board-input-capacitor-review-01/README.md)
records actual TDK selections and explicit initial/temperature budgets without
claiming verified bias/aging margins or making a substitution. Enable/input and
board-wide routing, electrical design and full release requirements remain open.

The [preceding U20 output checkpoint](staging/two-board-power-u20-output-native-02/README.md)
connects U20's four output capacitors to L20 and regulator PGND. Sixteen route
sections add 17 tracks and six paired through vias; no component or earlier
copper moves. Native checks show **2,478 opens**, zero geometry/parity/ERC errors
and two retained isolated-reference warnings. All 3,224 earlier connection
groups and both existing U23 zones/fills remain intact. The board has 2,216
tracks and 157 vias; all vias retain at least 0.165 mm drill-to-SMD clearance.
[Status-19](staging/two-board-fabrication-status-19/status.json) verifies 373 direct
bindings. The input network, feedback/configuration/enable and quiet/force
return planes remain unfinished. Exact capacitor derating, current/thermal
limits, stability and complete fabrication/installed-fit work remain open.

The [preceding U20 placement checkpoint](staging/two-board-power-u20-local-native-01/README.md)
regroups 20 U20 circuit parts and adds 22 front tracks forming 16 real connections.
P_J20/P_J21 return studs and the P_J106 internal control header are retired,
removing six isolated terminal opens separately. **2,486 opens** remain, with
zero geometry/parity/ERC errors and two retained isolated-reference warnings.
The 1,085-part board has 2,199 tracks and 151 vias. All 3,240 retained physical
connection groups, the remaining pin/net map, earlier tracks/vias and both U23
local planes are preserved. All eight layer views and local U20 front/back
views were inspected. [Status-18](staging/two-board-fabrication-status-18/status.json)
verifies 384 direct file bindings. U20 bulk input/output, control and return
routing remain incomplete. Former analog/digital return bars require qualified
PCB replacement paths and revised assembly/harness/support hardware before
release; connector retirement is not a completed return design.

The [preceding enable checkpoint](staging/two-board-power-buck-enable-native-01/README.md)
connects U23 EN, its R224 feed and a relocated R225 pull-down. A coordinated MODE
via/track replacement frees the package escape. Native checks show **2,508 opens**,
zero geometry/parity/ERC errors and two retained isolated-reference warnings.
Totals are 2,177 tracks and 151 vias. All 3,249 earlier connection groups are
preserved; every other copper object is unchanged. Both local planes are refilled
and remain connected, retaining all previous plane contacts and sense-reference
coverage. Eight native layer views and five local details were inspected.
The shared-enable DC scenario screen passes its declared allocations, but full
current/voltage/temperature/partial-power guarantees remain open.
[Status-17](staging/two-board-fabrication-status-17/status.json) verifies 625 file
bindings. Wider source distribution, other critical circuits and full
fabrication/installed-fit requirements remain unfinished.

The [preceding input-plane checkpoint](staging/two-board-power-buck-input-native-01/README.md)
connects U23's two bulk input capacitors and both VIN/PGND branches using two
bounded local planes. Three component moves, 15 tracks and 12 vias close seven
connections: **2,511 opens**, zero geometry/parity/ERC errors and two retained
isolated-reference warnings. The board now has 2,169 tracks and 150 vias.
All earlier copper and 3,256 connection groups are preserved. Each new filled
plane is one connected region; the In1 plane covers the In2 sense trace's
projection apart from its own via clearances. That geometric check does not
qualify return impedance, noise, thermal behavior or the full board-wide planes.
[Status-16](staging/two-board-fabrication-status-16/status.json) verifies 587 file
bindings. Enable/source distribution, other critical circuits and full
fabrication/installed-fit requirements remain open.

The [preceding sense/configuration checkpoint](staging/two-board-power-buck-control-native-02/README.md)
closes seven connections for U23 output sense, FSEL/MODE and N_U28's local bypass.
Two configuration resistors move closer to the regulator; values and the entire
pin/net map stay unchanged. The selected In2 sense route has 1.15 mm minimum
projected copper-edge clearance from SW/BOOT copper. The first native-clean
trial ran beneath a switch-node land and was superseded after this additional
review. Configuration returns join the existing quiet AGND group; its deliberate
PGND-plane connection remains pending.

Native checks find **2,518 opens**, zero geometry/parity/ERC errors and two
retained isolated-reference warnings. Twenty-one tracks and eight vias bring
totals to 2,154 tracks and 138 vias. All prior copper and 3,263 physical groups
are retained; all vias pass the drill-to-SMD screen at a 0.165 mm minimum.
Eight copper layers and four local details were inspected. Input/source bypass,
enable, planes, other critical circuits and full electrical/process/installed
fit remain unfinished. See [status-15](staging/two-board-fabrication-status-15/status.json).

The [preceding output-bank checkpoint](staging/two-board-power-buck-output-native-02/README.md)
regroups U23's four output capacitors and connects the local output/PGND bank.
It closes **eight physical connections**, reaching **2,525 opens**, with zero
native geometry/parity/ERC errors and two retained isolated-reference warnings.
Seventeen tracks and six conventional vias are added; totals are 2,133 tracks
and 130 vias. All prior copper, all 3,271 native connection groups and the full
schematic pin/net map remain intact. Four component moves pass the recorded
courtyard/context checks; all vias retain at least 0.165 mm drill-to-SMD clearance.
The initial native trial's copper-sliver warning was resolved using shared
trunks, without suppressing rules. Eight native layer views and both local
front/back details were inspected. Output sensing, wider supply/return planes,
other critical cells and full electrical/process/installed-fit review remain
unfinished. [Status-14](staging/two-board-fabrication-status-14/status.json)
binds the current evidence and retains the fabrication hold.

The [preceding bootstrap-return checkpoint](staging/two-board-power-boot-return-native-01/README.md)
reconciles the internally connected SW pins in U20/U23. Dedicated bootstrap-return
nets join each capacitor only to pin 13; force pin 10 remains assigned to the
inductor. TI documents the internal connection. The resulting **2,533 opens**
exclude two redundant external routing obligations; no physical connections
were added. Native geometry/parity/ERC errors remain zero, with two retained
isolated-reference warnings. An independent audit preserves all 5,967 native
objects and 3,271 physical groups, and restores the exact previous pin partition
when the declared internal bridges are applied. All board geometry and existing
copper previews are unchanged. See [status-13](staging/two-board-fabrication-status-13/status.json).

The [preceding power placement/routing checkpoint](staging/two-board-power-buck-local-native-01/README.md)
closes 16 local U23 regulator connections using 22 front-side tracks and no new
vias. R220/R221 move to the feedback side, and a smaller 100 nF / 50 V boot
capacitor permits 2.02/1.79 mm boot/return paths. The previously unrouted N_U28
buffer moves with its local bypass capacitor to free the feedback region.
The seven-section schematic retains 1,088 parts and 3,424 pin entries. Native
checks find **2,535 opens**, zero geometry/parity/ERC errors and the same two
isolated-reference warnings. The independent audit preserves all 3,287 prior
native connection groups, all earlier tracks/vias and the complete pin/net map.

Totals are 2,116 tracks and 124 vias. Every via still passes the drill-to-SMD
screen, with a measured minimum of 0.165 mm. The five affected footprint locations
pass their recorded receiving/context checks; C221 is the only part/land-pattern
substitution. All eight native copper views and a magnified U23 view were
inspected. The preceding [connector-retirement checkpoint](staging/two-board-power-buck-cell-native-01/README.md)
removed I_J2/P_J101 and their obsolete inlet copper leaf. No additional connector
is removed in the current local-routing change.

U23's output network, input/return planes and FSEL/MODE/enable still need work. U20, AUX and other critical cells
require regrouping; the N_U28/N_C67 local bypass needs routing. Effective
capacitance, loaded electrical/thermal behavior, process and full installed fit
remain unqualified. Eight of the 52 originally rejected source nets are now
connected and 44 remain incomplete in the current full native graph.

The module branch now implements the TPS26601RHFR timer-operated replacement
identified by the [cutoff review](staging/two-board-module-cutoff-review-01/README.md),
with its separate RTN reference and revised current/ramp settings. The independent
audit rejects 16 deliberate circuit/package faults. The fault delay is nominal,
and the startup envelope remains an engineering assumption with little margin.
Individual module containment, temperature/threshold/partial-power and loaded
timing checks, module receiving, deep-UV recovery, critical placement and routing
remain open. The [first-article plan](staging/two-board-power-native-10/MODULE-FIRST-ARTICLE.md)
sets out future physical tests. See the
[current two-board status](staging/two-board-fabrication-status-15/status.json).

The table is generated by `python -m hardware.fabrication.audit_scope` from
[scope.json](scope.json). [current-readiness.json](current-readiness.json)
records source hashes, saved native findings and unresolved requirements.

| Functional role | Selected development source | DRC findings / opens / ERC findings |
| --- | --- | --- |
| power supply | [KiCad source](../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/power_p03.kicad_pro) | 0 / 0 / 0 |
| input protection | [KiCad source](staging/input-protection-native-01/rear_inlet.kicad_pro) | 0 / 0 / 0 |
| rail disconnect | [KiCad source](staging/e28-branch-cleanup-native-12/rail_disconnect.kicad_pro) | 0 / 0 / 0 |
| rail monitor | [KiCad source](staging/rail-monitor-reserved-closed-native-02/rail_monitor.kicad_pro) | 0 / 0 / 0 |
| processor carrier | [KiCad source](staging/processor-carrier-native-01/processor_carrier.kicad_pro) | 0 / 0 / 0 |
| control inputs | [KiCad source](staging/control-inputs-native-01/control_inputs.kicad_pro) | 0 / 0 / 0 |
| led driver | [KiCad source](staging/led-driver-native-01/led_driver.kicad_pro) | 0 / 0 / 0 |
| converter | [KiCad source](../electronics/converter/converter.kicad_sch) | No PCB layout |
| input range | [KiCad source](staging/input-range-native-01/input_range.kicad_pro) | 0 / 0 / 0 |
| adc driver | [KiCad source](staging/adc-driver-native-01/adc_driver.kicad_pro) | 0 / 0 / 0 |
| dac receiver | [KiCad source](staging/dac-receiver-closed-native-01/dac_receiver.kicad_pro) | 0 / 0 / 0 |
| output stage | [KiCad source](staging/output-stage-native-01/output_stage.kicad_pro) | 0 / 0 / 0 |
| sequenced bypass | [KiCad source](staging/bypass-closed-native-03/sequenced_bypass.kicad_pro) | 0 / 0 / 0 |
| negative startup protection | [KiCad source](staging/nf-logic-swap-clean-native-01/negative_startup_physical.kicad_pro) | 0 / 138 / 2 |
| fan health protection | [KiCad source](staging/fan-watchdog-land-native-01/fan_power_health.kicad_pro) | 0 / 0 / 0 |

The [shared audio integration candidate](staging/audio-main-integration-04b/audio_core.kicad_pro) combines input range, ADC driver, codec, DAC receiver, output stage and sequenced bypass
into 329 parts/971 terminals on one proposed PCB.
Its native schematic export has zero ERC findings. The codec land remains
unassigned; the source and interface audit does not adopt separate development-board copper.
The [partial main audio PCB](staging/audio-main-controls-06/audio_core.kicad_pro) places 328 known electrical footprints
and six proposed mounts in the 150 × 63 mm allocation. Native geometry and ERC
are zero with all categories enabled. The missing ESS footprint remains an explicit
parity finding; 208 connections remain unrouted.
Its 99 local feedback/bypass/pump/clock/servo cells meet their declared endpoint
limits. Full analog performance, codec placement, mating/harness fit and manufacturing remain open.

![Partial main audio PCB](staging/audio-main-controls-06/plots/top.png)
All 131 declared local signal/supply endpoints and all 20 declared local ground-return pairs are native-connected.
The In1 AGND plane connects every one of the 200 placed ground pads to the input ground.
The candidate has 2425 tracks and 382 conventional 0.60/0.30 mm vias;
the minimum screened drill-edge-to-SMD gap is 0.170 mm. Twelve sensitive-node plane openings
and six mounting-hardware copper exclusions remain protected. All amplifier placements and
their direct compensation capacitor traces are retained. Four previously unrouted parts
have renewed receiving after local changes. Full power/return, noise/stability, stack/process
and whole-unit thermal/mating/harness qualification remain unfinished.
All 161 placed supply/sense pads connect to their designated sources; all earlier local/control/ground pairs remain connected.
Wide 0.60 mm outer-layer routes and short 0.20 mm necks complete the placed rail connections.
The divider feed alone uses a 9.74 mm 0.20 mm global branch with a separate low-current construction assessment.
Codec supply lands are still missing. Rail capacity/drop, return/noise, fault/thermal and process qualification remain open.
A further 57 low-speed control joins retain the earlier seventeen control pairs;
7 control connections remain open. Sensitive analog regions are protected on all routed layers.
Timing, signal integrity, coupling, EMI and installed fault behaviour still require qualification.
The settling supervisor, two capacitors and local pull-up have renewed receiving in the unchanged board allocation.
Two further control joins and its timing path are native-connected; the earlier watchdog timing pair remains intact.
U208.1 uses a dedicated 10.073 mm, 0.20 mm SENSE branch; supply and pull-up feeds keep their separate short entries.
The role/current/trace-drop assessment is conditional and does not establish installed noise, timing, fault or process acceptance.
Two additive codec-run/timer-ready branches preserve every parent component pose and authored copper object.
Those codec branches total 53.862/40.544 mm and three vias each; coupling, timing and installed loading remain unqualified.
Two additional bypass-sense/bias-window branches retain all earlier circuitry and placement.
Their lengths are 113.774/76.433 mm with one/two new vias; all existing width, clearance, via-count and length construction limits remain unchanged.
These longer routes still need installed loading, timing, return/noise, coupling and fault qualification.
The additional ANALOG_OK branch closes through 122.441 mm and two new vias without changing earlier circuitry or placement.
Its installed timing, loading, return/noise, coupling and fault behaviour remain unqualified.

The [combined digital/control candidate](staging/digital-four-clean-native-03/digital_core.kicad_pro) places the processor carrier,
control expanders and LED drivers on one proposed notched 114 × 60 mm PCB.
It has 138 electrical parts, zero native geometry/parity/ERC findings,
and 143 unrouted connections. All native categories are enabled.
Five inter-board headers were removed. Placement does not establish routed
power/return performance, production connector acceptance or installed fit.
The DC04 signal-routing checkpoint preserves all 201 connected power/ground pads,
39 local connections and 33 thermal connections. The four-layer stack, component
poses, mounts, outline and all DC03 copper remain unchanged. Both plane fills remain connected.
Its 1,252 tracks and 243 vias include 107 new drills clearing SMD copper by at least 0.169 mm.
The 21 earlier mask-covered heat-spreader vias retain their separate process hold.
SD and audio data nets are connected, but SD carrier trace totals span 47.6–84.3 mm
with unequal via counts. Timing, impedance, return paths and off-board interfaces remain unqualified.
The 116 open nets include 76 LED outputs and 13 control nets. LED/control escapes
and SD routing need rework before power/noise/thermal and manufacturing acceptance.
See the [signal-routing review](staging/digital-four-clean-native-03/README.md).
The separate [coordinated SD/LED routing trial](staging/digital-coordinated-native-01/README.md)
reduces SD carrier length spread to 6.00 mm with one via per signal and evaluates renewed placement/escapes.
The retained [six-layer checkpoint](staging/digital-native-spacing-native-01/README.md) has 71 opens.
The latest [eight-layer routing comparison](staging/digital-led16-closed-native-01/README.md)
has **27 opens** and zero native layout/parity/ERC findings with every check category enabled.
All prior pad connections are preserved, including 201 power/ground pads, 39 local,
33 thermal and all 32 front-control connections. All four actual plane copper unions remain connected.
The board has 3,342 tracks and 535 vias. SERIAL_0 and 26 LED outputs remain open.

CONTROL13 is now [40.498 mm with one via](staging/digital-control13-shortened-native-01/README.md),
down from the 107.197 mm/six-via detour introduced during LED10 closure. Rerouting the
entire net between its connector and IC pads removes that penalty and is also shorter
than its 42.305 mm/four-via pre-repair route. The released routing space enables LED16
to connect through 53.962 mm and one via. LED16 adds twelve tracks and one via; every
existing copper object and component pose is preserved relative to the CONTROL13 parent.

LED09 remains 124.070 mm/one via and LED10 remains 173.462 mm/four vias. The prior
SERIAL_1 and CONTROL30 shortening remains exact. Both new checkpoints pass eleven
focused tests each. The latest twelve added tracks have at least 0.203657 mm measured
nearby foreign-copper clearance, and the new via is independently checked against native copper.

Recursive auditing checks 8,597 source bindings with only the same two disclosed
historical NF test mismatches; all 213 current unit-source bindings match. Eight
layers and two regions on all signal layers were visually reviewed for each new
checkpoint. Twenty-one exposed-pad process holds remain; SD planar spread is 5.999239 mm.
All six sequential orders for LED13, LED14 and LED16 yielded one completed route;
LED16 was the shortest. This does not prove that multiple routes are globally impossible.

The [2026-11-04 continuation review](staging/digital-routing-continuation-27-01/README.md)
records twelve unsuccessful follow-up searches and one rejected native LED30 trial.
That trial closes LED30 but disconnects U3002.30 from LATCH, retaining 27 opens
and introducing two dangling-track warnings. It is not adopted; the verified
LED16 board and all current unit selections remain unchanged.

This remains a development comparison. The eight-layer stack, manufacturing process,
route loading, settling, timing, return paths, current/headroom, thermal and EMC
performance remain unqualified. Selected four-layer DC04 and whole-unit fabrication
holds are unchanged. Earlier milestones and tradeoffs remain in the linked checkpoint history.

The [AP04 arrangement](staging/assembly-layout-04/README.md) fixes allocations for the next PCB work:
six audio roles on the left, combined digital on the right, an upper rail-monitor
board, and the existing touch-module front bay. Its eight functional PCB
allocations exclude additional panel/emitter boards and the touch module.
The full current assembly, supports, harness and thermal design remain unfinished.

![Proposed board arrangement](staging/assembly-layout-04/arrangement.png)

DRC findings include warnings. A zero count does not approve the circuit,
fabrication process, current capacity, thermal design, mechanical fit or assembly.
All selected native reviews retain explicit rule coverage; no ignored category
is used to obtain a passing result. The NF isolated-domain ground warnings
remain visible; the negative reference nets have not been shorted to AGND.

## Work remaining before prototype release

- Select one coherent set of current board, panel, housing, link, return and harness sources.
- Reconcile mechanical receiving with thin NF/FPC and current E28/P03 rather than inherit older assembly passes.
- Resolve exact parts, fasteners, connector keying and manufacturing tolerances.
- Produce and independently inspect Gerber, drill, stack, BOM, placement and fabrication/assembly drawings for each selected physical board.
- Create the bounded first-article inspection and isolated bring-up package before complete-unit power-up.

Board-specific holds are recorded in scope.json. The missing ESS package
drawing, PCB process questions and prepared supplier request are in
[manufacturer-inputs.md](manufacturer-inputs.md). No supplier request or order
has been sent. The converter footprint remains deliberately unassigned.

A prototype release needs the completed design, inspected fabrication outputs
and a first-article inspection/bring-up plan. Measurements of the subsequently
built hardware are required for production qualification.

## Runtime and storage

Mac KiCad/OpenSCAD remain disabled. Native checks use the pinned, network-disabled
Linux CAD container. Routing development runs bounded host geometry searches.
Original projects and earlier candidates are preserved. Staging files are
engineering evidence, not a manufacturing release. Bulk audio generation stays paused.
