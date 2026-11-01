# Dual-fan under-base prototype

This is a **mechanical receiving and space proposal**, not a demonstrated cooling
solution or an adopted product configuration. All 23 current native cases pass.
It provides an actual tray, two guards and four spacers, with fan/fastener
receiving gauges. It is not yet combined with the enlarged base's complete
actual solid, holes, thermal lands and attachment stack.

| Proposed geometry | Value |
| --- | --- |
| Tray | 334 × 188.4 mm; 1.5 mm deck and 2 mm perimeter walls |
| Fan centres | (80,165.5) and (254,165.5) mm |
| Maximum fan body receiving box | 40.5 × 40.5 × 12.5 mm before separate registration space |
| Nominal outlet plenum | 6 mm below the metal base |
| Rear outlet | 266 × 14 mm, between retained rails |
| Guard plates | Two 44 mm nominal squares, 1 mm thick; separate from the tray |
| Foot mounting change | 2 mm tray flange plus 6 mm spacer; existing feet translate down 8 mm |
| Foot retaining screw proposal | M3 × 20 replacing M3 × 12; nominal engagement remains 5.8 mm |
| Nominal overall height with PS01 knobs | 104 mm, compared with the 87.6 mm original reference |

The height is nominal and does not bound bumper compression, manufactured
parts or loaded stability. Exact foot fasteners and stack compatibility still
need the enlarged-base construction audit. All meshes remain at assembly
coordinates: [tray](generated/tray_geometry.stl),
[guards](generated/guard_geometry.stl), [spacers](generated/spacer_geometry.stl)
and [complete receiving scene](generated/assembly.stl). Material, joining,
manufacturing method, strength and vibration are unapproved.

The [manufacturer's detailed drawing](https://cdn.noctua.at/media/26bc7ca5/Noctua%20NF-A4x10%20FLX%20Specification.pdf?download=true)
specifies the padded fan size and dimensional tolerance used here. Its
without-pad dimension differs from the current product page; the discrepancy
is retained. The official CAD has eleven valid nominal solids and approximately
12.383 mm overall thickness. That model was inspected only for external
mechanical dimensions. Its modified impeller geometry is not used for airflow
simulation. Manufacturer files remain external and are not redistributed;
`fan-source.json` binds their URLs and hashes.

The H20 declared 1,037-pin pattern needs **77 whole pins removed**, leaving
960, to clear the fan and foot-column receiving areas. No thin pin remnants
are proposed. Original pins intersect the fan receiving volumes by
2,916.0005 mm³; that nonempty witness remains retained. The remaining pin
gauges clear the tray, fan and swept fastener receiving regions. This changes
the cooling geometry, so no H20/CH20/IH20 thermal result is inherited.

Mount registration uses a shared floating bolt axis, not a fixed shaft forced
through displaced holes. The stress allocation combines ±0.30 mm fan
registration (20% above ±0.25), ±0.15 mm half-pitch tolerance and ±0.10 mm tray
hole location, per axis. For actual hole centres A and B, the same straight
bolt axis is placed at their midpoint. Its offset relative to either hole is
then at most ±0.275 mm per axis. The maximum Ø3.1 shank gauge clears both the
fan's Ø4.2 minimum-hole model and the tray's Ø4.4 nominal-hole model, including
their polygon conservatism. This proves a geometric assembly construction
under the declared allocations; preload, bearing, thread retention, rotational
misregistration and actual manufactured tolerances remain unqualified.
The half-pitch offset assumes a symmetric nominal pattern. Pitch tolerance
alone does not certify the grid's absolute position relative to the frame;
that receiving assumption also needs manufacturer applicability or inspection.

The rejected fixed-axis witness is retained (51.1147 mm³ interference). The
earlier 22-case trial is preserved under `history/`; it predates the complete
registration-contract review and does not establish the current mount result.
The current set includes 12 empty intersections, eleven nonempty solids or
witnesses, and three 0.008 mm³ controls. Raw mesh volumes and topology are
reviewed separately; the tray is one closed connected boundary, with two guard
and four spacer boundaries.

Two fan loads provisionally add 0.11 A / 1.32 W at 12 V using the detailed
document's rating tolerance. These are planning values, not startup/stall/fault
bounds, and are **not yet included in the operating supply/load ledger**.
Power source, protection, tach wiring and temperature/fan-failure response
remain unimplemented. See `electrical-and-test-holds.json`.

Published free-air flow and pressure do not establish installed flow, heat
transfer or noise. Actual cut-pin geometry, duct leakage, guards, tabletop
clearance, source heat paths and motor heat require a new thermal assessment
and physical measurements. The existing metal-wall/lid assumptions cannot
be credited to a plastic housing. This remains a candidate to test against
the retained load and 20% heat stress, not a cooling pass or fabrication release.

```sh
.venv/bin/python -m hardware.cad.a12.thermal.forced_air_prototype.build \
  --openscad /path/to/OpenSCAD
```
