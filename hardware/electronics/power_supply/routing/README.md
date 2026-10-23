# Main-supply copper in progress

This editable candidate starts from the checked E24 157-component placement.
The parent `power_supply.kicad_pcb` and immutable E24 review ZIP retain the
placed-only snapshot; **this directory is the current routing work**.

The digital 5 V buck has explicit input, output, feedback, soft-start and enable
paths. Both input and both output bulk capacitors, bypass, bootstrap, soft-start
and feedback divider sit on front copper with U2/L4. C63 moves to (43.2, 11.7)
to make room for C21. Its raw-generator loop remains unfinished. R8/R9 stay on
the underside outside thermal regions.

The analog 5.8 V pre-buck now has the same categories of connections. U3/L5
rotate and move closer, and its critical capacitors/divider move to the front.
The pre-rail feeds both IN pins of U9 and the J4 engineering test pin. Feedback
senses U9's IN land separately from the power feed. R12/R13 remain on the back.
C57/C58 move clear of U3's thermal reserve; their linear-regulator circuit still
needs layout refinement. J3 moves 0.3 mm to make space for C28. Part values,
rail targets, header pin maps and schematic nets are unchanged.

The digital sense trace starts at J3's source-output pin. Sensing an upstream
capacitor would leave the power trace's DC drop to J3 uncompensated. R11 and R16
have separate low-current returns to their respective buck IC ground pins on
In4. Four pour keepouts isolate the return vias from the In1 power plane. The
long sense/return paths, source-to-load ground displacement, copper/contact
drops and actual loop stability remain unqualified against the voltage targets.

One filled In1 region serves both bucks. Explicit ground spines allow path
checks without relying on zone connectivity. Conventional via drills stay at
least 0.25 mm outside every solder land, including same-net lands. Four all-layer
copper keepouts retain 3.7 mm mounting clearance. The actual native saved fill
is retained for review; stackup, copper/via losses and heat spreading are open.

Native KiCad checks report **zero all-severity nonrouting/track DRC and
schematic-parity issues, 273 open connections, 219 segments and 53 vias**.
The checker measures 53 segment/via paths, imposes minimum widths on power
connections, requires 24 critical parts on the front, and rechecks all 157
part/net contracts, exposed-pad rails, outline, holes and thermal reservations.
Thirty-six tooling tests pass, including reserved floating-RT net names after
IC rotation, a removed U9 power feed despite its intact sense connection, and
quiet-return shunts. These are geometry/connectivity checks, not proof of
regulation, noise, current capacity, startup or operating temperature.

The [TI TPS62933F layout guidance, pp. 40–41](https://www.ti.com/lit/ds/symlink/tps62933f.pdf)
informs the same-layer critical parts, bypass and separate output sense. Raw
boost/Cuk generators, precision sources and linear regulators still need
placement/routing, return/shielding and thermal copper/vias. Input harness
behavior, EMI, startup, late switch closure and large-capacitor loop stability
remain open. No regulator is approved for power-up from this record.

Six proposed layers do not establish a production stackup, ampacity, heatsinking
or EMC performance. Actual housing fit, heights, leads, harnesses, assembly and
physical electrical/audio/thermal tests remain open. This directory is **not a
fabrication/assembly release** and the unit is not build-ready.

From the repository root:

```sh
python3 -m hardware.electronics.power_supply.routing.generate --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.power_supply.routing.check --kicad-cli /path/to/kicad-cli
```

Generation resets this candidate from E24 and removes its old verification and
filled snapshot. The parent PCB stays unchanged. Open this directory's PCB/
project for copper work and the parent's schematic for circuit review. The
checker fills/saves an isolated matching project for native parity, retaining
that board at `generated/filled.kicad_pcb`. The editable input has the zone
boundary; its saved fill is in the review snapshot. Native exports, clearances
and source hashes are in [generated/verification.json](generated/verification.json).
The [placement packet](generated/placement.json) records current courtyards for
future housing work; its datum and physical fit are unverified. Source paths
in the verification record are relative to this directory. Evidence is stale
if the report is absent or any hash no longer matches. No new firmware build,
mechanical render or physical-test result is claimed.
