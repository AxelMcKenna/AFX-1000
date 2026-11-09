# BYPASS_SENSE and thermal-branch repair: 31 opens

This eight-layer comparison connects BYPASS_SENSE, restores CODEC_RUN and
LATCH_5V, and relocates one external LED-driver ground via. Native Linux KiCad
reports 31 opens and zero geometry, schematic-parity or ERC findings, with
every category enabled. The selected four-layer DC04 remains unchanged.

| Net | Previous total copper / vias | Current total copper / vias |
| --- | ---: | ---: |
| BYPASS_SENSE | 22.591244 mm / 1, open | 98.693358 mm / 5, connected |
| CODEC_RUN | 227.955205 mm / 12 | 241.606315 mm / 12 |
| LATCH_5V | 199.915051 mm / 12 | 223.524163 mm / 15 |

The BYPASS addition is 76.102115 mm with four new vias. Two CODEC_RUN tracks
are replaced by a 20.665919 mm back-side route, and two LATCH_5V tracks by a
32.474658 mm route with three new vias. Overall, four tracks are retired,
59 tracks at 0.20 mm and seven 0.60/0.30 mm vias are added. The board contains
3,236 tracks and 525 vias.

The external U3004 ground via moves from (100, 27) to (99.5, 25.7) mm while
retaining its identity, 0.60 mm copper and 0.30 mm drill. Its exposed-pad branch
retains 1.00 mm width; the connection starts at (98, 28) mm inside the existing
pad. Branch length increases from 1.000000 to 2.745906 mm. Every component
pose, pad assignment, undeclared copper object, outline, mount and authored
zone remains exact. Thermal performance still requires qualification.

Independent replay verifies every prior pad group and every unaffected net
record. All 201 power/ground pads, 39 local connections, 33 thermal branches
and 32 front controls remain connected. All four physical plane unions remain
connected. SD spread stays 5.999239 mm with one via per signal. Minimum
non-exempt drill-to-SMD clearance remains 0.154984 mm; the 21 mask-covered
heat-spreader vias retain their process hold.

The minimum checked copper gap across the new tracks and changed 1 mm ground
branch is 0.201342 mm against the unchanged 0.200000 mm native rule. The final
continuation uses a tighter planning margin; native rules and manufacturing
requirements are not relaxed. Physical stack, process capability, timing,
coupling, return transitions and EMC remain unqualified.

Conditional receiving passes for 138 components and five mounts. All eight
copper plots and four 1200 dpi details were inspected. The focused suite
passes 145 tests, including protection against a narrowed thermal branch,
altered drill, undeclared endpoint, pad reassignment, missing restoration
evidence and routing back to an isolated source stub.

The [search review](routing-search-review.json) preserves the rejected first
native trial and the subsequent corrections. It is not used as passing
evidence. A [fresh native-group survey](../digital-native-group-regions-31-01/diagnosis.json)
includes existing track interiors and conductive crossings; all 31 remaining
nets still lack a path under the declared retained-copper planning geometry.
This directs further coordinated rework without claiming global infeasibility.

Evidence: [native review](review.json), [connectivity](stage-connectivity-review.json),
[independent replay](bypass-ground-signal-review.json), [physical review](corridor-audit.json),
[conditional receiving](conditional-assembly-review.json), [visual review](visual-review.json),
[construction](../digital-bypass-ground-signal-repair-03/construction.json),
and [native project](digital_core.kicad_pro).

Remaining digital connections are 29 LED outputs, SERIAL_0 and SERIAL_1.
The comparison remains unselected and unreleased. Audio/NF routing, approved
ESS package/interface data, actual stack/process, installed assembly,
electrical/thermal/fault qualification and the current first-article package
remain unfinished.
