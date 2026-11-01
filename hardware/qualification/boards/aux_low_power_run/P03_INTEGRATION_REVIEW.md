# P03 integrated AX03 transmitter — software-layout review

The matching low-power RUN transmitter is now integrated into a separate
**264-part P03 candidate**. Fresh isolated Linux KiCad checks report **zero DRC
errors, zero warnings, zero opens, zero ERC and zero schematic-parity findings**,
with every native rule category enabled. This is not a fabrication or physical
qualification release.

- [Preferred paired KiCad project](../../../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/power_p03.kicad_pro)
- [Actual top copper, component bodies and outline](../../../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/closed-top.svg)
- [Native results](../../../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/review.json)
- [Exact conservation and source/receiver handoff](../../../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/handoff.json)

`CURRENT_LAYOUT.json` in the candidate directory identifies this project. The
PCB at that directory's root is an incomplete staging parent. Canonical P03,
the combined source and the strict-centering source remain unchanged.

## Circuit and geometry

Eight parts implement the existing AX03 proposal: TPS389001DSET supervisor,
SN74AUP1G17DCKR source buffer, 100 kΩ RESET pullup, 10 MΩ pulldown, 1 kΩ output
resistor, two 100 nF bypass capacitors and a 10 nF timing capacitor. Bench-only
headers from the source-cell drawing are omitted.

The internal POWER_RUN node retains the original U102 PG, J104 switch and R113
3.3 kΩ topology. The new supervisor senses this internal node. **J106 pin 3 alone
changes from raw POWER_RUN to POWER_RUN_E28_LEAF**, driven by the source buffer
through 1 kΩ. The E28 U43 receiver still drives the original U28 input; no latch,
fault or independent READY function is bypassed.

The board remains **160 × 45 mm, six layers, 1.6 mm nominal**. All 266 original
strict-source footprints remain exact except the declared J106.3 net assignment.
All 1,254 original vias and every retained original track remain exact. Only
unused POWER_RUN signal branches are removed. Mounts, outline, stackup, setup,
geometry rules, zone settings and keepouts remain exact. The eight added parts
are on the front; only the new supervisor moved 0.5 mm during fanout work.

The [strict-centering repair](../../../electronics/power_distribution/p03/candidates/strict-native-centering/README.md)
was composed with the new transmitter using an exact three-way object merge;
there were no conflicting edits. Its previously documented limitations carry
forward, including two 0.333542 mm P19_SRC necks changing from 0.8 to 0.6 mm.
The earlier 0.2 A calculation is a diagnostic, not a qualified source-current
limit. The new holes, routes and filled polygons require fresh power, return,
thermal and fault-energy extraction.

## Local bypass evidence

An independent [local path inventory](../../../electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/local-bypass-inventory.json)
uses actual authored tracks, actual native pad electrodes and actual via barrels.
It permits no zone shortcuts and stays inside a bounded local cell.

| Capacitor connection | IC terminal | Nominal path | Route |
| --- | --- | --- | --- |
| C402 AUX | U201.4 | 2.873 mm | Front copper |
| C402 ground | U201.2 | 2.425 mm | Front copper |
| C401 AUX | U202.5 | 5.735 mm | Front and In2 copper, two barrels |
| C401 ground | U202.3 | 5.310 mm | Front copper |

These are centreline/electrode diagnostics using the nominal stack, not measured
impedance, loop inductance, effective capacitance, noise or assembly acceptance.
The trial to force the buffer supply onto the front created CAD conflicts and
was rejected; its raw findings remain preserved. The preferred project is the
zero-finding candidate identified above.

Five new 0.60/0.25 mm vias overlap SMD copper at C403.2, C401.1, U103.5, R402.1
and R403.2. They require an explicit filled-and-capped receiving process. Their
native filling/capping metadata is unspecified, and no supplier has accepted the
drawing/metadata reconciliation or the complete C50 process. These requirements
are additional to the preserved source's existing via-process limitations.

## Logical source-to-receiver map

| P03 | Signal | E28 |
| --- | --- | --- |
| J106.1 | AUX | J5.1 |
| J106.2 | AGND | J5.2 |
| J106.3 | Buffered RUN | J5.3 |
| J106.4 | Independent source READY | J9.2 |

This is a pin contract, not a completed harness. P03 uses a keyed 2.50 mm XH
connector; E28 J5/J9 are currently generic 2.54 mm headers. They do not form a
direct mating pair. Connector selection, keying, the READY branch, strain relief,
wire order and physical continuity/receiving tests remain open.

Six cross-board regression tests use the actual exported native netlists. They
reject a raw-RUN bypass, an E28 receiver bypass, a supervisor package-pin swap,
a READY/RUN shortcut and a changed original PG pullup. Existing AX03 current and
threshold counterexamples remain in the regression suite.

## Remaining qualification

The existing 90 mA allocation, 100 mA regulator rating and supply voltage are
unchanged. The actual-band AUP input-current and Schmitt threshold assumptions
remain receiving requirements, not manufacturer guarantees or measurements.
The E28 board still has 52 unresolved force/return warnings. Full-unit fit,
new-component receiving, harness, airflow, thermal/PDN/fault tests, startup,
partial power, line-open/short behavior and loaded cutoff measurements remain
release gates. All physical and fabrication flags remain false.

Primary part references: [TI TPS3890](https://www.ti.com/lit/gpn/tps3890),
[TI SN74AUP1G17](https://www.ti.com/lit/ds/symlink/sn74aup1g17.pdf),
[KEMET C0603C104K5RACTU](https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU)
and [Vishay D/CRCW e3](https://www.vishay.com/docs/20035/dcrcwe3.pdf).

Mac CAD stayed disabled. All CAD operations used the pinned isolated Linux
KiCad image; bulk audio generation remains paused.
