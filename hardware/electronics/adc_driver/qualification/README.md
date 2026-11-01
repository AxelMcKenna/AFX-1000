# E12 ADC-driver qualification review

E12's original 79-part characterization PCB passes fresh native connectivity checks, but **fails the design review**: its continuous AGND planes cover the FDA summing/output pads, and its J2 sensing boundary does not close the final converter-pin feedback loop. Both negative-bias health monitors also remain absent. This directory preserves those findings and a bounded plane-opening repair trial. It does not grant fabrication, powered-test or complete-unit qualification.

## Actual design findings

[TI THS4551 Rev. D](https://www.ti.com/lit/ds/symlink/ths4551.pdf), §12.1, calls for plane openings around capacitive-sensitive input/output pins and minimal summing-node trace length. The original native-filled In1/In4 polygons cover all eight relevant FDA pad centres. No dielectric/material stackup is assigned. Pad dimensions, routed node copper and unspecified plane spacing therefore introduce unquantified capacitance into a design whose external feedback capacitors are only 1 pF.

The same manufacturer describes 0.6 pF internal feedback capacitance. Combined nominal feedback capacitance is therefore approximately 1.6 pF before board/package parasitics. The simple 1.21 kΩ RC poles are 131.5 MHz for external capacitance alone and 82.2 MHz for the nominal sum. These are illustrative RC calculations, **not gain/phase margins**. The existing hypothetical two-pole sensitivity model does not replace the manufacturer model with actual ADC switching loads.

Real copper witnesses also expose the high-frequency power-loop scope. Each FDA positive/negative 100 nF bypass path sums about 6.89/8.89 mm of visited trace centre-lines and traverses two vias. LM7705 flying-capacitor paths sum approximately 9.95 mm with two vias per lead. TI's [LM7705 guide](https://www.ti.com/lit/ds/symlink/lm7705.pdf), §9–10, calls for short low-ESR capacitor connections and close input decoupling. No invented millimetre threshold is used to declare these loops stable. A compact local placement, extracted loop impedance and actual pump/ripple tests remain required.

The J2 force/sense stars are real, but both functions share one conductor per ADC polarity after that header. Output force witnesses are asymmetric in length/layers. They do not sense the voltage at the ESS pins through the harness. The final hardware needs ADC-driver/codec co-location or a revised force/sense interface.

## Conditional electrical and manufacturing screens

The E12 supply allocations yield a THS4551 total supply interval of 5.0838–5.356 V, leaving only 44 mV below its 5.4 V recommended maximum. This is a steady-state interval; it does not establish startup, overshoot or partial-power behavior. The existing modeled headroom has about 17.1 mV differential peak reserve to the codec's **typical** 2 Vrms full scale. Without a guaranteed minimum range and real gain calibration, that is not a clipping guarantee.

The manufacturer's ±1 V/µs supply turn-on/off stress limit also requires a real edge-rate check at each FDA's actual supply pins. Staying below that bound is necessary; it does not qualify arbitrary current, startup, turn-off or audio behavior.

There is also a concrete allocation mismatch: the proposed negative-bias health window permits −0.16 V, but the existing worst-case internal output after DC-error allowances is about 0.13388 V. This leaves only 0.29388 V of headroom, below the project's stated 0.30 V reserve. Under that conditional model, the bias upper bound would need to be no greater than approximately −0.16612 V **before** comparator tolerances and dynamic margins. The health-window specification requires revision; this calculation does not approve a new threshold or prove physical clipping.

The original netlist's reference divider has 500 kΩ Thevenin resistance. An extra 0.2 nA of board leakage would shift its midpoint by 0.1 mV; with a 10.35 V aggressor difference, that implies 51.75 GΩ isolation. These examples show sensitivity and are not newly approved leakage limits. Hot amplifier bias, real capacitor leakage, cleaning/coating, humidity and board contamination need separate allocations and measurement. The original stage-only noise estimate excludes pump/rail/reference/aliasing and other system stages; it cannot be relabeled as complete-chain SNR.

The native DGK lands have 0.65 mm pitch, 4.225 mm row-centre spacing and 1.625 × 0.50 mm pads. TI's example uses 0.65 mm, 4.4 mm and 1.4 × 0.45 mm respectively. This is an alternate library pattern; dimensional difference alone is not a proved footprint failure. Its 0.15 mm pad gap, mask/paste/process tolerances and actual assembly yield remain fabrication prerequisites. Passive MPNs, capacitance under bias, resistor errors/leakage and connector parts are not fully selected.

## Separate plane-opening trial

`plane-opening-trial/adc_driver.kicad_pcb` appends eight copper-pour-only rule areas on In1/In4. A 0.5 mm pad margin is an explicit **trial allocation**, not a manufacturer-specified parasitic limit. Existing components, pads, traces, vias, board outline and original zones are unchanged. No whole-system datum or final board replacement is implied.

Fresh native refill reports **0 DRC issues, 0 schematic-parity issues and 0 opens** for both original and trial. The trial removes actual filled copper beneath all eight target pad centres. Existing local feedback, header force/sense and ground-reference construction checks still pass. Full sensitive-node relief, selected stackup, return-current effects and manufacturer-model/physical stability remain unqualified. The trial is not a final layout or production release.

## Reproduce and use the evidence

```sh
uv run --locked python -m hardware.electronics.adc_driver.qualification.native \
  --kicad-cli /path/to/kicad-cli
uv run --locked python -m hardware.electronics.adc_driver.qualification.audit
uv run --locked python -m hardware.electronics.adc_driver.qualification.audit --check
uv run --locked python -m unittest discover -s tests/tooling -p test_adc_qualification.py -v
```

`generated/native-original/` contains fresh exports made into a redirected output folder; frozen E12 inputs were not rewritten. `generated/native-plane-trial/` contains the separate native refill/DRC evidence. `trial-verification.json` binds the trial to source hashes and records its limited scope. `review.json` records measured copper geometry, conditional calculations, failed/blocked findings and all remaining physical gates. Native DRC return code zero means the checker ran; its actual issue, parity and open counts are separately inspected.

`measurements.json` names the required real-board metrics and identifies manufacturer limits, project allocations and missing acceptance criteria. Seven physical measurement groups remain unrun/blocked. Unknown loop, leakage, gain, stage-noise, thermal or EMI limits cannot become passing results. Zero physical tests have been performed by this review.

## Bounded external manufacturer-model run

`spice.py` uses the actual native left-channel R1–R6/C1–C5 connections and TI's unmodified seven-terminal THS4551 PSpice model, downloaded from [TI's SBOMB92B package](https://www.ti.com/lit/zip/sbomb92b). Model bytes remain external; the receipt records their SHA-256, subcircuit terminal order, simulator/code-model hashes, netlist hashes, raw vectors and logs. It uses ngspice 45.2 with PSpice compatibility and the bundled matching XSPICE code models. The independent RC check verifies 0.5 − j0.5 at its known corner before the stage runs.

Six AC sweeps from 10 Hz to 100 MHz completed without solver warnings. The nominal differential transfer at 1 kHz is 0.4859418877 V/V. Scenarios vary static per-pin resistance (221/260/299 Ω), a differential resistance, and illustrative extra input/output capacitance. These are declared hypotheses, not measured parasitics or an ESS switching-input model. Closed-loop phase does not supply phase margin.

The DC results expose an unresolved model/load problem. The two original per-pin-ground sweeps starting at −6 V emitted solver warnings; their raw data and logs are retained and rejected for numerical comparison. Zero-start forward/reverse sweeps avoided warnings, but at zero input the nominal per-pin-ground outputs still average approximately 1.21049 V despite fixed VOCM = 1.65 V. A simple static estimate including the 3.32 Ω output resistors is approximately 1.62920 V. The differential-load case averages approximately 1.64901 V. This discrepancy remains unexplained; even warning-free ground-load DC vectors do **not** establish hardware headroom, clipping or a verified vendor-model operating point. No model was rewritten to hide it.

```sh
python -m hardware.electronics.adc_driver.qualification.spice \
  --library /path/to/libngspice.0.dylib \
  --code-models /path/to/matching/ngspice-code-model-directory \
  --vendor-model /external/path/ths4551.lib
```

Running this external solver is optional in portable CI. The mandatory portable tests check native stage/pin contracts, deck parameters and saved result hashes without downloading TI models or loading KiCad/ngspice. `generated/vendor-spice/verification.json` records twelve bounded cases, two rejected solver cases, and the unresolved common-mode discrepancy. Ideal supplies/VOCM/input buffer exclude the real servo, reference, pump, supervision, partial power and switched ADC loading. No full-board stability, physical qualification or fabrication approval follows from these runs.
