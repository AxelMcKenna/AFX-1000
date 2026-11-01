# E12-R2 design repair candidate

This separate 94-component candidate preserves frozen E12 and its qualification trial. It adds both negative-bias window monitors, a V5 supervisor, separate force/sense terminals, compact local bypass routing, declared plane openings and a complete candidate stackup. It remains incomplete for fabrication: final ESS integration, its real input-current model, analog isolation/partial-power limits and physical qualification are outstanding. Asserting FDA PD does not isolate analog pins.

## Manufacturer-model discrepancy

The unmodified TI THS4551 model and terminal order pass TI's supplied differential-load fixture. With the original ground-referenced 260 Ω static loads, the internal common-mode control clamps about 3.822 V above its internal midpoint, leaving 423 mV error. Changing only the declared load reference to 1.65 V restores approximately 1.64903 V output common mode. This isolates the numerical common-mode current burden; it does not establish the actual ESS input behavior. Original failed data remains preserved, and TI model bytes remain external.

Five R2 vendor-model cases exercise the actual native FDA R1–R6/C1–C5 stage and declared force/sense line hypotheses. Supplies, input buffer and VOCM are ideal. These cases exclude the actual servo, reference, pump, switching input and protection. Closed-loop phase does not establish phase margin, and no cable length is approved.

## Hardware monitor and headroom repair

A TLV9024DR implements an upper and lower window on each NBIAS rail. Each rail is shifted through 100 kΩ/10 kΩ into a positive sensing domain. Shared 161 kΩ/10 kΩ and 240 kΩ/10 kΩ dividers set the upper/lower references. Exact corners include a declared 0.12% lifetime/assembly resistor allocation, guaranteed full-temperature ±2 mV comparator offset and a 0.6 mV CMR/PSR/leakage allocation.

| Conditional calculation | Result |
|---|---:|
| Upper trip interval | −0.183982 to −0.172765 V |
| Lower trip interval | −0.285929 to −0.274091 V |
| Filtered pump allocation after changing the series resistor to 0.1 Ω | −0.256 to −0.20198 V |
| Maximum total FDA supply at the proposed P03 V5 maximum | 5.310929 V |
| Actual-R2 linear-screen minimum internal output after allocations | 0.144875 V |
| Headroom at the weakest upper trip | 0.317640 V |

The actual-R2 ideal-MNA screen uses an explicitly ideal co-location sense boundary, 4.06 Vrms source, 3.2–3.4 V reference allocation, offsets/leakage, 0.15% gain-resistor allocation and 3% output-resistor allocation. It passes the existing 0.30 V reserve allocation. Those inputs are conditional engineering allocations; actual ADC loading, guaranteed minimum full scale, aging and measured clipping/THD are still missing.

All four comparator outputs inhibit TPS3808G50DBVR MR. Its guaranteed RESET low is 0.4 V, which cannot directly guarantee shutdown relative to a negative FDA supply. Each FDA therefore uses 47 kΩ series and 68 kΩ pull-to-own-NBIAS PD translation. Including 3% resistance allocation and 100 nA FDA PD bias, the static off level is at most 0.41829 V above VS−; the on level is at least 1.28608 V when external enable is at least 2.7 V. TI specifies off below 0.55 V and on above 1.15 V relative to VS−.

The supervisor provides a specified 12–28 ms release delay after valid V5 and bias. Dynamic shutdown, residual negative-bias charge, rail sequencing and actual MCU levels remain system/physical gates. Current TLV9024 Rev. H removed the former POR feature; comparator POR is not assumed. DRV_ENABLE must remain low until ±12 V, codec and reference health are valid.

## Reference, leakage and layout

The reference divider changes from 1 MΩ/1 MΩ to 100 kΩ/100 kΩ, reducing Thevenin resistance from 500 kΩ to 50 kΩ. Additional 0.2 nA leakage shifts 10 µV instead of 100 µV; a 5 nA amplifier-bias screen gives 250 µV instead of 2.5 mV. Reference loading increases to 16.5 µA at 3.3 V and needs ESS approval.

Servo feedback resistance changes from 100 MΩ to 10 MΩ, and both sensing resistors from 100 kΩ to 10 kΩ. This reduces summing-node current/leakage sensitivity tenfold and retains finite DC gain of 2000. With the 1 µF film capacitor, integral crossover rises from 3.183 Hz to 31.83 Hz. The faster common-mode loop requires coupled-loop and noise validation; its behavior is not covered by the FDA-only manufacturer run.

FDA bypasses use one short power via under the IC body to backside 0402 capacitors. Flying capacitors sit directly behind the pumps, with adjacent vias outside their solder lands. Summing branches and 1 pF feedback capacitors remain on F.Cu. Explicit openings cover their pad/branch regions, and routing masks exclude unrelated inner/backside tracks there. Native fills and real trace/via witnesses are checked independently. No parasitic-capacitance or RF-impedance extraction is claimed.

The candidate stackup has six 35 µm copper layers and 0.10/0.28/0.63/0.28/0.10 mm dielectric layers, totaling 1.60 mm. FR4 Dk 4.2, loss tangent 0.02 and ENIG are provisional fabrication inputs. Actual materials, dielectric tolerances, mask/paste and process approval remain outstanding. The 110 × 78 mm outline and four M2 mounting positions are retained.

All passives have manufacturer ordering-code candidates in components.json. Selections include TNPU gain resistors, PLT precision monitor/reference dividers and KEMET 1 pF ±0.1 pF C0G capacitors. Actual 47 µF reserve/output candidates use X7S, with ±22% temperature change, and the 10 µF/50 V parts use realistic 1206 footprints. Effective capacitance, ESR, DC bias/aging, hot leakage, availability and assembly remain validation gates. Manufacturer characteristic curves are not worst-case guarantees.

J2 provides separate routed force and sense conductors for each ADC polarity. This is an intermediate interface; final integration should co-locate the driver and converter, close each sense trace at its actual pin, and qualify loading, parasitics and power-off injection. No cable is approved and no complete protection claim is made.

## Reproduction

Use local KiCad and a separately downloaded official TI model:

```sh
python -m hardware.electronics.adc_driver.revision2.generate --kicad-cli /path/to/kicad-cli
python -m hardware.electronics.adc_driver.revision2.headroom
python -m hardware.electronics.adc_driver.revision2.route --kicad-cli /path/to/kicad-cli
python -m hardware.electronics.adc_driver.revision2.native --kicad-cli /path/to/kicad-cli
python -m hardware.electronics.adc_driver.revision2.model_review --library /path/to/libngspice --code-models /path/to/code-models --vendor-model /external/ths4551.lib
python -m hardware.electronics.adc_driver.revision2.simulate --library /path/to/libngspice --code-models /path/to/code-models --vendor-model /external/ths4551.lib
python -m unittest discover -s tests/tooling -p test_adc_revision2.py -v
```

External solver execution is optional in portable CI. Mandatory tests verify saved source/evidence hashes, topology mutations, monitor/PD corners and physical-release flags without downloading models. Zero physical tests have been performed. Fabrication, build-ready and full-board stability flags remain false.
