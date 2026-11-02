# E13 R83 manufacturing review — unreleased

This is a review packet for the separate
[R83 land candidate](../rail-monitor-r83-land-native-01/README.md). It is one
rail-monitor board, not the complete standalone unit. Its selected parent board
and the fabrication inventory have not been replaced by this export.

The candidate has zero native DRC findings, opens, ERC or schematic-parity
findings. The files below reproduce its current geometry; they do not establish
electrical qualification or fabrication/assembly acceptance.

| Deliverable | Contents |
| --- | --- |
| [Gerbers](gerbers/) | Four copper layers, two masks, two pastes, two legends and the profile; X2 attributes, absolute original coordinates, mm, 4.6 format |
| [Drills](drills/) | Separate PTH and NPTH Excellon files, decimal mm; drill maps and report |
| [Review BOM](assembly/review-bom.csv) | 38 groups, 181 parts, proposed codes and explicit unresolved/unqualified status |
| [Placement](assembly/review-placement.csv) | 181 electrical parts; original KiCad rotations; mm, X right and Y up from the PCB origin; all parts on top |
| [Front assembly review](assembly/front-enlarged-review.pdf) | Enlarged native drawing for identification; use the raw front/back PDFs for the original 1:1 export |
| [Bare-board test netlist](test/rail_monitor.d356) | IPC-D-356A, 851 points; includes vias and four mechanical holes |
| [Independent CAM previews](previews/) | Four copper layers, front mask and front paste, parsed with PyGerber 2.4.3 at 20 pixels/mm |

## Checks completed

[The output inspection](manufacturing-inspection.json) checks all file hashes,
Gerber layer functions and units, the complete profile, every drill hit, and all
placement references, values, packages, coordinates, rotations and sides against
the native source. The centerline outline is **80 × 70 mm**. Drills contain
357 vias at 0.3 mm, 14 component holes at 1.0 mm and four NPTH holes at 2.4 mm.
The four mounting features H1–H4 are excluded from the 181-part BOM and placement
schedule. The CAD drill diameters still require supplier process confirmation.

Excellon coordinates round to 0.001 mm. Each axis matches the native coordinate
within 0.000500001 mm. Allowing that export rounding, the conservative via-hole
edge-to-SMD-copper lower bound is **0.10941485 mm**. Actual drill registration,
diameter, mask and assembly tolerances are still excluded and must be received.

[The IPC inspection](test/ipc-inspection.json) matches all 851 point identities,
net names and coordinates to the native source, including R83's changed lands:
476 SMD records, 371 plated records and four mechanical records. Long net names
retain their explicit aliases. KiCad's `CUST 0` means 0.0001 inch (0.00254 mm)
coordinate units, despite the millimetre Gerber/drill/placement files. The
maximum IPC axis quantization difference is 0.00126 mm. The format was checked
against the [pinned KiCad exporter](https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0.7/pcbnew/exporters/export_d356.cpp).
This checks the delivered netlist, not a manufactured board or CAM-extracted
copper connectivity. Request a supplier comparison and bare-board opens/shorts
test before assembly.

All four exported copper layers and the front mask/paste were independently
rendered and visually inspected. The native assembly drawing and drill maps
were also inspected. Individual preview images are tightly cropped separately;
they are not registered overlays or dimensional measurements.

## Manufacturing holds

The BOM has **55 unresolved order codes**: 51 capacitors and four connectors.
The 114 resistor codes are derived proposals requiring confirmation, and the
12 IC codes are schematic candidates awaiting complete process/qualification
acceptance. No BOM entry in this packet is marked production-approved. Part
substitution, orientation and assembly zero-angle confirmation remain open.

There is **no explicit material stackup in the source PCB**. KiCad nevertheless
generated a job file with a default stack, a 1.6 mm nominal thickness, `Finish:
None` and a stroke-inflated 80.05 × 70.05 mm size. Those values are not a supplier
contract. The original metadata is preserved as
[an explicitly unapproved JSON file](metadata/kicad-generated-job.UNAPPROVED.json),
outside the CAM directory and without a `.gbrjob` extension. Specify and receive
finished thickness, dielectric/copper stack, plating, finish, mask, stencil,
registration and panelization before releasing outputs.

The remaining E13 holds include exact precision/passive parts and installed
error budgets, finite PDN/return paths, noise/fault response, harness/mounting and
installed fit. The R83 candidate requires its own receiving checks. Converter
and other-board work remains part of the full-unit fabrication objective.

## Provenance and replay

[export-review.json](export-review.json) records the exact source hashes, pinned
Linux KiCad version, applied export recipe and generated file hashes. The source
PCB remained unchanged. [extra-native-commands.json](extra-native-commands.json)
records the additional native enlarged drawing and test-netlist commands.

```sh
python -m hardware.fabrication.inspect_rail_monitor_outputs --check
python - <<'PY'
import json
from hardware.fabrication.inspect_rail_monitor_ipc import ROOT, check
assert check() == json.loads((ROOT/'test/ipc-inspection.json').read_text())
PY
python -m unittest tests.tooling.test_manufacturing_coordinates tests.tooling.test_ipc_export_reader
```

The first export attempt failed during SDK metadata serialization. Its partial
outputs were removed and its small failure record retained in the adjacent
`rail-monitor-manufacturing-review-01` directory. This `-02` packet has the
completed export and independent inspections. No order, vendor upload or
external message was made. Mac CAD remains disabled.
