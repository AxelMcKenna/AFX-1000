# Main-supply routing candidate

This directory owns the higher-headroom standalone supply candidate, separate from the B1 budget design and the main checkout's A08 edits. It starts from the immutable E24 157-part placement and extends the PCB to **90 × 44 × 1.6 mm**, retaining six proposed copper layers and all four M2 fixing holes. The parent E24 PCB remains an 84 × 38 mm placed-only snapshot. Neither is a fabrication release.

The main supply now has complete native connectivity: both bucks, both ±17 V/±22 V boost/Cuk generators, +19 V/+12 V/analog 5 V linear stages, the negative reference, both negative SET targets and both negative regulators' input/output, ground, bypass and SHDN connections. Four raw-rail test-header feeds are connected. Schematic values and rail targets are unchanged.

KiCad 10.0.7 reports **zero all-severity geometry/library/all-track DRC issues, zero schematic-parity issues and zero open connections**. The PCB has **2,600 segments and 285 vias**. Independent checks measure **322 paths**, enforce widths/faces, separate SET drive/sense and quiet returns, and check all 157 pin/value contracts, outline, holes, conventional drills and thermal reserves. The tooling suite includes mutations for missing input straps, SHDN, output headers and raw test feeds, thinned load copper, missing physical via endpoints and disconnected filled spreaders.

Seven native saved fills are retained: In1 power ground, In4 analog 5 V output, underside +19 V/+12 V output spreaders, a front RAW_N22 input spreader and front/back RAW_N17 input spreaders. Each spreader's three declared thermal vias share an actual filled region. All analog 5 V source/bleed/header annuli remain in one In4 island. Positive regulator exposed pads carry OUT; **LT3090 exposed pads carry negative IN**. ILIM is strapped to IN for the internal limit. This establishes connectivity, not heat dissipation or fault/SOA approval.

The −19 V header path uses at least 0.8 mm track and measures 69.730 mm. The −12 V path uses at least 0.5 mm track and measures 53.085 mm. At the specified 50/150 mA loads, a provisional 35 µm copper/1.8e−8 Ωm estimate gives 2.24/8.19 mV trace drop against a 30 mV allocation. These estimates exclude vias, connectors, temperature and fabricated thickness; they are not ampacity or complete voltage-budget qualification. Fine-pitch OUT straps are checked separately at 0.35 mm. SHDN is fed from the existing positive digital rail. Conventional bypass/filter/bleeder escapes avoid solder lands. Single-face escape drills that became redundant after routing are removed.

Thirty-one In1 antipads isolate declared quiet vias and both film-filter ground lands. Four all-layer keepouts preserve 3.7 mm copper clearance from fixing centres. Conventional drills remain at least 0.25 mm from solder lands. Quiet In2/In3/In4 returns clear other power-ground vias and plated lands; the measured minimum copper gap is 0.164 mm. Actual copper-intersection checks reject a drive/sense merge before any regulator SET land and a power-ground shunt on the six checked negative-reference/target return terminals before J2. Same-net ground junctions are explicit on In1/In2/In3. These checks catch same-net contacts ordinary DRC permits.

The negative power routing uses available signal/surface layers and limited In1 sections. In1 therefore includes clearances around those routes; it must not be assumed to be an uninterrupted return sheet. Return displacement, switcher hot-loop refinement, noise, crosstalk and EMI remain open. The N19 SET sense can use In4 to leave its crowded pin corridor while preserving Kelvin separation and the filled analog 5 V output island.

Existing layout concerns remain. The +19 V input bypass is 12.906 mm, the +12 V source/header route is 67.406 mm and the N12 amplifier HF return is 15.885 mm. Negative precision returns and the relocated output bypass routes are recorded in [verification](generated/verification.json); their routing limits are not qualified stability/noise limits. Effective capacitance/ESR, real loop models, startup, all-rail charging, late closure, faults and thermal behavior require qualification. Design references remain the [LT3090](https://www.analog.com/media/en/technical-documentation/data-sheets/3090fa.pdf), [LT1634](https://www.analog.com/media/en/technical-documentation/data-sheets/1634ff.pdf), [OPA2192](https://www.ti.com/lit/ds/symlink/opa2192.pdf), [TPS62933F](https://www.ti.com/lit/ds/symlink/tps62933f.pdf), [LT3471](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3471.pdf) and [LT3080](https://www.analog.com/media/en/technical-documentation/data-sheets/3080fc.pdf).

[A10 housing integration](../../../cad/a10/README.md) retains its 334 × 157 × 38 mm RMX-style chassis and current component positions. This copper continuation changes no component pose, outline, mount or printed geometry. Its earlier native mesh/button/lever/collision evidence is retained after an exact spatial comparison, with current PCB hashes refreshed. Height, lead, header and harness dimensions remain conditional allocations; minimum allocated floor clearance is 0.35 mm. A09 retains frozen historical 84 × 38 mm supply inputs.

Other standalone PCBs, wiring and full-unit integration remain unfinished. Actual loss, stability/startup, thermal/EMI and physical electrical/audio/assembly tests remain open. **The complete unit is not build-ready; this record does not approve power-up or fabrication.** No new firmware build or physical test is claimed.

## Rebuild

From the isolated repository root with matching KiCad libraries and Python tooling:

```sh
python3 -m hardware.electronics.power_supply.routing.generate --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.power_supply.routing.check --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -v
```

Generation resets the candidate from E24 and removes stale verification/fill evidence. It produces an unverified routing candidate. The checker fills/saves an isolated matching project, checks parity, every native open and independent copper requirements, then certifies routing closure in source-hashed records. The saved native board is `generated/filled.kicad_pcb`. Evidence is stale if any recorded hash differs.

This continuation belongs to preserved higher-headroom commit `7abd80c928c1402ec783bfe170113efaa957e3f7` under `build/workspaces/high-headroom-standalone`. `SOURCE_REVISION.json` identifies the source base. The active main checkout and A08 edits remain untouched.
