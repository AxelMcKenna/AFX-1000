# NF06P physical layout and routing development

This is a development board, with **no fabrication release or physical
qualification**. It implements the [265-part NF05R circuit](../uv_recovery/),
plus two non-electrical mounting holes, inside a 149 × 39 mm allocation.
Older 231/233-part routing and enclosure results do not qualify this revision.

The six-layer layout uses F/In2/In3/B for signal routing, In1 for AGND and In4
for AUX2V6. There are 154 front and 111 rear components. The front packing
calculation leaves an area ratio of 1.246 after two 7.8 mm square mounting
reserves; this is an area measure, not a guarantee of routability or assembly
clearance. Fourteen named rear capacitors require 1.9 mm receiving height;
the other rear SMD receivers use 1.2 mm. These are unaccepted assembly
requirements pending exact parts and process reconciliation.

| Candidate | Native geometry / schematic parity findings | Actual missing connections | Scope |
| --- | ---: | ---: | --- |
| Original `negative_startup_physical.kicad_pcb` | 0 / 0 | 750 | Preserved initial placement |
| [Four-cap receiving repair](receiving_repair/generated/native-review.json) | 0 / 0 | 750 | Only C4/C5/C31/C32 move 0.6 mm in native v |
| `routing/first-six-layer-02/output.kicad_pcb` | 0 / 0 | 433 | First general routing trial, original poses |
| `routing/power-stitches/input.kicad_pcb` | 0 / 0 | 487 | Original poses, 173 literal vias and 342 local segments |
| `routing/centered-seeded-six-layer/output.kicad_pcb` | 0 / 0 | 241 | Combined partial routing, original poses |
| [Receiving detour](routing/receiving-detour/native-review.json) | 0 / 0 | 241 | Four-cap repair plus corrected nearby B-side signal route |
| [Current continuation repair](routing/receiving-continuation-repair-01/verified-review.json) | 0 / 0 | 204 | Four exact via-joint corrections and a missing WDO layer transition restored |

The latest independently reviewed partial route is the204-open continuation
repair. It retains all267 receiving-layout identities and all36 native keepout
polygons. Source geometry and native receipts remain preserved during the
[isolated restart](../../../../cad/a12/controlled_restart/README.md).

Counts come from native `GetUnconnectedCount(False)`, including hidden nets.
Stock KiCad 10.0.7 truncates the DRC missing-connection list at 499 markers;
the [independent report-limit review](../../../../cad/a12/qualification_reviews/kicad_report_limit/README.md)
records the uncapped method. A report of 499 is not the complete count.

The receiving-detour receipt independently compares all 267 footprint poses,
values, FPIDs, sides and pad nets against the four-cap repair. It accounts for
all 515 literal seed objects, with only the eight declared B-side cap endpoints
changed. Native refill/DRC reports zero geometry, warning and schematic-parity
findings, with 241 connections still missing. It uses 1,658 segments and 320
through vias. The generic 0.2 mm routing does **not** establish force-current
capacity, voltage drop, Kelvin accuracy, PDN impedance or noise performance.

Rejected imports and intermediate candidates remain in separate folders. The
unmodified seeded-router result had five uncentered via-joint findings; the
first combination with moved caps exposed a real nearby signal short. Those
results were corrected in successors. An audit also caught construction
metadata reading a live SWIG vector after mutation: its old-endpoint fields
are explicitly rejected in favor of independent saved-PCB comparisons.
Used driver copies preserve the exact versions that made those artifacts.

FreeRouting's seeded import reports fixed-clearance findings despite the
native-clean source. That representation/rule disagreement remains unresolved;
its internal score is not a validation pass. Each imported successor requires
fresh KiCad DRC, uncapped connectivity and exact pose/seed review.

Whole-unit [NF265/FPC91 receiving checks](../../../../cad/a12/enclosure_growth/nf265_fpc91/README.md)
retain their initial finite connector/tail conflicts and boundary artifact.
The four-cap repair is a new mechanical input and must receive its own checks.
The JST PH header's documented PCB thickness limit also conflicts with the
1.76 mm receiving scenario; the production stack/header choice remains open.
Startup, partial power, hot leakage, loaded cutoff, fault energy/SOA, shared
returns, installed cooling and prototype measurements remain unqualified.
