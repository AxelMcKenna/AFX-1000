# E10 stereo input range and preamplifier

The input-precharge discussion and false implementation flags below describe the
E10 snapshot. [E11](../sequenced_bypass/README.md) and
[F02](../../firmware/EXTERNAL-CONVERTER.md) now implement its independent
input-settling schematic/status/firmware sequence. Physical timing, E10/E11 PCBs
and enclosure placement remain open; E10's analog calculation record is unchanged.

[E12](../adc_driver/README.md) now implements a candidate downstream ADC driver
and reference-half servo while preserving this stage's high-impedance load.
Its scale, stability, partial-power protection, noise and physical behavior still
need qualification. The ADC-boundary discussion below records the original E10
open requirement rather than a current absence of all driver schematic work.

E10 is a **28-component native KiCad schematic prototype** for the stereo input
range relay, passive master attenuation, AC coupling and low-voltage FET
preamplifier. It ends at a single-ended PRE_OUT boundary. The ADC driver, raw-pin
bias/protection, independent input-settling sequence and PCB remain unfinished.
It is not ready to connect directly to the E09 ADC inputs or to fabricate.

Open the [project](input_range.kicad_pro), [schematic view](generated/input_range.svg),
[BOM](bom.csv), [pin schedule](components.json), [native verification](generated/verification.json)
or [loaded circuit analysis](generated/circuit-analysis.json).
The [E10 design review package](../../releases/README.md#standalone-review-e10)
contains current sources, drawings and earlier-stage evidence; it is not a
fabrication or assembly release.

## Signal path and interfaces

Released K1 selects master attenuation; energized K1 selects send/return. The
33.2 kΩ/13.7 kΩ divider stays connected in both modes. Its loading includes the
actual following network rather than treating the FET input path as infinite.
Attenuating before the buffer keeps the amplifier's input common mode well
within the ±12 V domain at the intended line peaks. This replaces the earlier
prospective high-voltage input buffer, whose input-pair crossover needed review.

Each channel then has a 4.99 kΩ current-limiting resistor, a nonpolar 1 µF film
coupling capacitor, a 68 kΩ DC return and a 47 pF C0G RF shunt. One OPA1656 dual
package supplies both channels at nominal noninverting gain 1.365. A 33.2 Ω output
resistor isolates each PRE_OUT. The final gain resistor and ADC gain calibration
remain open; changing that resistor requires rerunning DC, noise and headroom
checks, not simply scaling the nominal AC result.

| Boundary | Connection / requirement |
| --- | --- |
| J1 | PROC_IN_L, AGND, PROC_IN_R; same order as E03 J3 pins 1–3 |
| J2 | PRE_OUT_L, AGND, PRE_OUT_R; future ADC driver input, load ≥100 kΩ |
| J3 | P12, AGND, N12; externally generated/qualified regulated ±12 V |
| J4 | 5 V, GAIN_LOW; same order as E02 J5 and E05 J3, second gain coil |

The two gain coils share E02's gain driver. They select input/output ranges
together; they do not determine wet/dry routing. The receiver's line source is
modeled at 100 Ω for nominal/tolerance AC checks, with 1–1000 Ω sensitivity cases.

At 1 kHz into 100 kΩ, the model gives approximately 4.017 V RMS PRE_OUT for the
master full-scale target 12.283 V RMS, and 4.006 V RMS for the send/return target
3.162 V RMS. These are preamplifier interface levels, **not established ADC full
scale**. The minimum screened input impedance is 27.75 kΩ, above the 22 kΩ target.
Worst listed tolerance cases stay within about 0.064 dB at 20 Hz and 0.025 dB
at 20 kHz relative to 1 kHz for this stage alone.

## Input precharge must be implemented

E02/E03 currently energize the processing-input isolation relay and wet-output
selector together on BYPASS_LOW. That gives this circuit **no independent input
settling interval** before processed audio is selected. Pin compatibility does
not establish a working integrated sequence. The verifier freshly exports the
actual E03 schematic and records that the two coils still share this net.

E10 allocates at least 1.2 seconds after the input is connected to a source
of ≤1 kΩ, with output selection held dry. The worst modeled input time constant,
including capacitor/resistor corners and the RF pole, is about 91.14 ms.
The hypothetical 48 V step residual is about 0.126 mV after that interval. With
allocated hot bias, capacitor leakage and offset, the combined preamp DC screen
is about 20.4 mV within a provisional 25 mV allocation. Those component allocations
are not measured or jointly guaranteed at temperature.

Implement an independently qualified input-coil drive and input-settled status,
then update the external firmware's startup/rearm policy before integration.
E09's timer runs on converter/DAC conditions before this input relay closes;
it cannot be counted as this input precharge interval. F01's existing 350 ms
rearm delay also does not implement the required sequence. Gain changes,
manual bypass release and input/power faults must restart the input qualification.
The extra expander has available status inputs; no extra MCU pin assignment is
approved here. Relay/contact timing and bypass transients still need measurement.

## Protection, noise and geometry limits

The 4.99 kΩ resistor screens a conservative 48 V input/capacitor polarity step
to less than 9.63 mA, with about 0.462 W initial resistor power and 1.267 mJ maximum
capacitor-step energy. This uses the OPA1656 absolute input-current bound as a
design screen. It does not prove internal clamp behavior, reverse-power safety,
raw ADC pin protection, rated surge/ESD performance or an assembled fault test.
The exact 1 W resistor, pulse/voltage/temperature derating and capacitor leakage
still need qualification.

The unweighted 20 Hz–20 kHz own-circuit noise model gives about 2.84 µV RMS at
PRE_OUT in master and 1.88 µV in send/return, or 8.69/1.49 µV input referred.
It includes resistor Johnson noise and a typical OPA1656 colored-noise model;
it excludes the ADC driver/converters and other system noise. It does not prove
the complete unit's A-weighted S/N targets. Keep the original targets and close
the complete noise budget before approving the audio architecture.

The ±12 V/1% supply screen leaves over 4.8 V of modeled output peak reserve
using a conservative 1.3 V rail allowance. That allowance comes from an open-loop
test range, not a guaranteed swing specification. One dual package dissipates
about 0.187 W quiescent typically at nominal rails, or 0.243 W at the screened
hot/current/high-rail limits. Signal power, junction temperature and enclosure
thermal performance remain unmeasured.

The WIMA MKS2C041001F00KSSD candidate has nominal 7.2×5×10 mm body and 5 mm pitch;
the standard footprint matches that nominal body/pitch with 0.75 mm holes.
Its fabrication/assembly fit remains unqualified. The relay land pattern is
checked against the manufacturer's drawing. Neither these parts nor the E08/E09
parts have been placed in the current enclosure clearance report.

## ADC boundary remains open

ESS figure 42's input driver uses 536 Ω series and 432 Ω ground shunts. The
datasheet's 260 Ω ADC input impedance is not explicitly identified as per-pin or
differential. The analysis records both balanced small-signal interpretations;
they give substantially different loaded gain. Neither is approved by assumption.

The driver also takes an external BiasD supply. With an illustrative 3.3 V
reference and no net ADC DC current at its target common mode, the output
shunts would require about 3.697 V amplifier common mode to deliver 1.65 V at
the ADC pins; the drawing's equal bias divider would need about 7.394 V BiasD.
This conditional calculation is **not a bias recipe or the ADC's DC input
model**. Resolve reference loading, raw-pin AC/DC behavior, protection and loaded
driver rail/headroom before implementing the remaining ADC stage.

## Regeneration and verification

```sh
python3 -m hardware.electronics.input_range.generate
python3 -m hardware.electronics.input_range.verify --kicad-cli /path/to/kicad-cli
```

The generators use Python's standard library. The verifier imports the existing
project-owned numerical/netlist helpers and records their hashes. It checks
native all-severity ERC, all 28 exported pin/value contracts, fresh E02/E03/E05
interfaces,24 ideal AC cases against an independent closed form,64 allocated DC
cases,1,024 mode/tolerance cases at three frequencies, additional voltage
corners,36 finite-gain sensitivity cases and 81-point noise integration per mode.
These are linear/design-allocation screens, not transistor stability/distortion,
clock, dynamic-relay, physical-fit or audio-performance evidence.

Primary sources: [OPA1656](https://www.ti.com/lit/ds/symlink/opa1656.pdf),
[Omron G6K](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf),
[WIMA MKS2](https://wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf),
[ESS ES9292PRO](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf).
Document hashes are recorded in [dependencies.json](dependencies.json).
