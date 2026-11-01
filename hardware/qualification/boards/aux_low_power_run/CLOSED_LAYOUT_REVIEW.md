# E28 closed-layout review — 1 November 2026

The E28 AX03 control-board candidate is fully routed in the checked KiCad
project. This is a software-layout milestone; fabrication and physical
qualification remain withheld.

The preferred candidate includes the completed signal-stub cleanup. Review the
[paired KiCad project](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/rail_disconnect.kicad_pro),
[actual top-copper plot](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/closed-top.svg),
or [native results](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/review.json).
The older PCB at the work directory root is a preserved parent;
[CURRENT_LAYOUT.json](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/CURRENT_LAYOUT.json)
identifies the preferred project.

| Check | Result |
| --- | --- |
| Native uncapped open connections | 0 |
| Hard DRC errors | 0 |
| ERC / schematic parity findings | 0 / 0 |
| Ignored native rule categories | None |
| Electrical parts / mechanical footprints | 271 / 4 |
| Remaining warnings | 33 dangling tracks, 19 dangling vias; none hidden or waived |

The 70 × 5.5 mm wing, U38/C81 positions and housing dimensions are unchanged
from the previous eight-open candidate. Nearby narrow control traces were
detoured and the remaining nets joined on the two added layers. Existing
force-track and force-via objects were preserved. New drills change filled
plane clearances, so power/return resistance, thermal and fault-current evidence
must be refreshed; connectivity alone does not establish those limits.

## Signal-copper cleanup

The previous closed-layout candidate had 153 native warnings. The preferred
successor removes 3,589 unused narrow signal-track segments and 90 unused signal
vias. Every removal set retains zero uncapped opens, and the final saved board
passes a fresh native zone refill, all-severity DRC, ERC and schematic parity.
KiCad's own endpoint test follows the unused branches; the via-layer test first
matches the actual source DRC before being used during the cleanup.

The [exact-object audit and warning inventory](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/cleanup-review.json)
confirm that every retained track and via is exact. All main force, four internal
MOSFET common-source, AGND and AUX copper objects match the original closed
candidate. Sixteen internal-power stubs caught during review were restored before
selection. No footprint pose, pad, body, courtyard, mounting hole, stackup,
outline, keepout or zone setting changed. Filled polygons were refreshed and
their electrical/thermal qualification remains open.

Three J12 silkscreen strokes were clipped to leave 0.29 mm nominal clearance
to the board edge. A matching project-local footprint library keeps the native
library-mismatch check enabled without changing the preserved parent library.
The captured wing receiving envelope is unchanged; the existing clearance screen
therefore still applies to that envelope, without qualifying the whole unit.

The remaining 52 warnings are individually listed as unresolved: six concern
preserved force copper and 46 concern preserved return/AUX copper. They require
electrical/thermal disposition and have not been excluded from DRC or accepted
for fabrication.
The previous project and handoff remain preserved; `CURRENT_LAYOUT.json` points
to the cleaned successor and retains its previous-project link.

## Explicit manufacturing profile

Exactly one E28_OUT_READY through-via uses a 0.50 mm land and 0.20 mm drill.
Its nominal annular ring remains 0.15 mm. The checked project lowers the minimum
through-hole diameter from 0.30 to 0.20 mm and audits that this is the only
smaller via. Clearance, annular-ring, hole-spacing and other rule settings are
unchanged. The preserved parent project retains its original settings.

This is a mechanically drilled, filled and capped through-via proposal. Supplier
acceptance is required, including the full mixed 80/35 µm eight-layer stackup,
plating, fill, cap planarity and drill interpretation. The following are proposed
receiving limits, not measured or accepted manufacturing tolerances:

| Proposed limit | Value |
| --- | --- |
| Maximum finished board thickness | 1.782 mm |
| Plated bore before filling | 0.18–0.22 mm |
| Minimum etched land diameter | 0.48 mm |
| Maximum radial hole registration error | 0.025 mm |
| Worst bore aspect ratio | 9.90:1 |
| Required aspect capability with the 1.2 factor | ≥11.88:1 |
| Worst remaining annular ring | 0.105 mm |
| Supplier minimum-ring capability required with the 1.2 factor | ≤0.0875 mm |

PCBWay publishes 12:1 and a 3 mil annular ring in an advanced capability table;
that table does not approve this particular board or the combined process.
[Manufacturer capability reference](https://www.pcbway.com/advanced-pcb-capabilities.html).
The specified fill and copper cap must be confirmed explicitly;
[JLCPCB's process description](https://jlcpcb.com/help/article/pcb-via-covering)
explains the distinction from ordinary tenting. No order or fabrication release
has been issued.

## Captured mechanical receiving screen

The isolated Linux OpenSCAD
[positive witness](../../../cad/a12/controlled_restart/results/control-wing-positive/result.json)
produces the expected 0.125 mm³ solid. The
[assembly intersection](../../../cad/a12/controlled_restart/results/control-wing-receiving/result.json)
is empty against eleven captured CP01 meshes, NF265/FPC91 receiving boxes and
conservative vertical board slabs.

The wing envelope includes ±0.15 mm XY/Z placement allowance, up to 1.8 mm PCB
thickness and 2 mm above-board component allowance. Clearance to the inflated
front-connector boxes remains 0.90 mm. The intentional join to the old board
material is excluded. Mac CAD stayed disabled; both operations used the guarded
2 GB, 2 CPU, 60-second Linux runner without retries.

This screen does not qualify the complete updated assembly, harness, airflow,
mounting stiffness or manufactured fit. Those checks, the 52 remaining native
warnings, the [P03 transmitter's](P03_INTEGRATION_REVIEW.md) remaining process and
physical acceptance, AUX/input-current and
threshold measurements, PDN/thermal/fault tests and prototype bring-up remain
release gates. The complete RMX unit is not yet build-qualified.
