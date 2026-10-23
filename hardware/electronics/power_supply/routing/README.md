# Main-supply copper in progress

This editable candidate starts from the checked E24 157-component placement.
The parent `power_supply.kicad_pcb` and immutable E24 review ZIP retain the
placed-only snapshot; **this directory is the current routing work**.

Both buck candidates have explicit input/output power, feedback, soft-start
and enable connections. Their critical capacitors and dividers sit on the
front with their switching ICs and inductors. The analog 5.8 V pre-rail feeds
both U9 IN pins and the J4 engineering test pin. Its feedback senses U9's IN
land separately from the power feed. R8/R9 and R12/R13 remain underneath;
C57/C58 clear U3's thermal reserve. J3 moves 0.3 mm to make space for C28.

The ±17 V LT3471 stage now includes its boost and Cuk switch paths, transfer
capacitor, rectifiers, inductors, output banks, divider/reference networks,
feedforward capacitors and RC startup controls. Sixteen critical parts are on
the front. C67–C69, the feedforward/startup capacitors and R48–R50 remain on
the back. The negative output reaches C56, the linear-regulator input capacitor;
U11's IN/EP connections and the rest of that linear stage remain unfinished.
C61/C62 move clear of U13's thermal allocation; their RAW_N22 supply-bypass
connections still need routing. All schematic values, rail targets and pin maps
are unchanged.

The digital sense starts at J3's source-output pin; analog pre-rail sense starts
at U9 IN. R11 and R16 return separately to their buck IC ground pins on In4.
The raw-stage divider and reference bypass return separately to U13's exposed
pad on In3. Seven pour keepouts isolate these quiet-return vias from In1;
tracks on their unused layers must also clear the vias. Actual source-to-load
ground displacement, trace/contact losses, feedback noise and loop stability
remain unqualified. Some feedback and startup paths are long; measured path
limits are geometric regression guards, not electrical-performance limits.

One filled In1 region serves the three switching stages. Explicit power-ground
spines allow path checks without relying on the fill. Conventional via drills
stay at least 0.25 mm outside every solder land, including same-net lands.
Four all-layer keepouts retain 3.7 mm mounting clearance. The saved native fill
is retained for review. Copper weight, stackup, via losses and heat spreading
still need qualification; the reserved thermal regions are not heatsinks.

Native KiCad reports **zero all-severity geometry/library/track DRC and
schematic-parity issues, 219 open connections, 510 segments and 87 vias**.
The checker measures 105 segment/via paths, imposes minimum power-path widths,
requires 24 buck and 16 raw-stage critical parts on the front, and rechecks all
157 part/net contracts, exposed-pad rails, outline, holes and thermal reserves.
Forty-three tooling tests pass, including removed Cuk/bulk/startup feeds,
insufficient negative power width, same-net via-in-land and quiet-return shunts.
These checks do not prove regulation, noise, current capacity, startup or
operating temperature.

The [TI TPS62933F layout guidance, pp. 40–41](https://www.ti.com/lit/ds/symlink/tps62933f.pdf)
and [LT3471 layout discussion](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3471.pdf)
are design references. The ±22 V raw generator, precision sources, linear
regulators and remaining distribution still need placement/routing refinement,
return/shielding and thermal copper/vias. Input harness behavior, EMI, startup,
late switch closure and large-capacitor loop stability remain open. No regulator
is approved for power-up from this record.

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
