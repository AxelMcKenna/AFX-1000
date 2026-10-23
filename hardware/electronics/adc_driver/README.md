# E12 stereo ADC driver and bias servo

E12 adds a 79-component native schematic between E10's preamplifier and E09's
raw ADC pins. It implements a candidate input driver and common-mode bias
circuit. **It is not a fabrication release.** Actual ADC loading, amplifier
stability, protection under partial power, calibrated scale, complete weighted
noise, negative-bias supervision and PCB placement remain open.

Open the [native schematic](adc_driver.kicad_sch),
[exported drawing](generated/adc_driver.svg), [BOM](bom.csv),
[interface contract](integration.json), [verification](generated/verification.json)
or [circuit analysis](generated/circuit-analysis.json).

## Circuit

An OPA1656 dual unity buffer presents a 1MΩ return plus FET input to each E10
output. This preserves E10's ≥100kΩ load contract while driving the lower
resistance ADC gain network. Each THS4551 converts the buffered single-ended
signal to differential, with nominal gain1.21k/2.49k =0.48594. Its resistive
feedback senses the actual ADC pins after the3.32Ω output resistors. Local1pF
feedback and raw-pin RF capacitors are provisional compensation parts; trace,
package and ADC switching capacitance must be included before layout approval.

An OPA4192 quad uses separate amplifiers to buffer each ADC reference half and
servo each raw pin-pair average. The1MΩ/1MΩ reference divider draws about1.65µA
per channel at3.3V, with a filtered midpoint. Two100kΩ sense resistors measure
the raw-pin average; a1µF film feedback capacitor and100MΩ parallel resistor
provide slow common-mode correction with finite DC gain. The servo includes
the output-resistor drop and typical FDA common-mode error. It does not assume
that raw ADC pins draw zero DC current. The two channel references stay separate.

The raw drivers run from4.90–5.10V and separate LM7705 negative-bias generators.
The filtered negative rails are allocated−0.256 to−0.1838V, including a20mA
load,1Ω filter drop and an explicit5mV ripple allowance. This gives useful
low-output headroom while keeping the normal signal-driver rails inside the
ADC's−0.4…+6V absolute input limits. Those absolute limits are not operating
targets or a proof of fault protection. The actual ripple/transient allowance
and load interpolation must be measured.

The modeled maximum driver current is16.45mA across the stated load/resistor
corners. Adding1.92mA FDA quiescent current and1mA extra allocation gives19.37mA per
bias generator, below its characterized20mA load point. Fast ADC current pulses
and bypass-capacitor currents are not included in that static screen.

The±12V domain supplies only the input buffer and slow reference/servo quad.
It does not directly supply the raw ADC output amplifiers. The servo reaches
VOCM through10kΩ and a BAT54S clamp pair to ground/5V. Series-current calculations
are recorded, but combined internal clamp currents, hot diode leakage, rail
back-power, regulator faults, stored charge and short-circuit behavior remain
unqualified. Do not interpret this as completed surge/ESD or single-fault protection.

## Interfaces and qualification

| Connector | Pins in order |
| --- | --- |
| J1 preamplifier | PRE_OUT_L, AGND, PRE_OUT_R; matches E10 J2 |
| J2 converter | ADC_LP, ADC_LN, AGND, ADC_RP, ADC_RN, REF_ADC1, REF_ADC2; matches E09 J2 |
| J3 power | P12, AGND, N12, V5_REG |
| J4 control/sense | AGND, DRV_ENABLE, NBIAS_L, NBIAS_R |

DRV_ENABLE connects to E09 J5.8 CHIP_EN. Its receiving pull-downs keep both FDAs
disabled when that signal is absent. The bias pumps run whenever5V is present.
The **future PRE_ANALOG_OK circuit must monitor both filtered negative rails**
within−0.27…−0.16V as well as the main analog/5V rails before CHIP_EN can assert.
That window-monitor circuit is not implemented in E12. Supply slew must also
meet the THS4551's1V/µs maximum turn-on/off requirement.

The linear reference-filter/servo settling screen is comfortably within E10's
1.2-second interval. It uses allocated dominant time constants and a typical
VOCM input load. Saturated startup, power sequencing, interrupted bias and
large-signal recovery still require transient modeling and physical tests.
E11/F02 remain responsible for dry routing and the independent input sequence.
Raw ADC and reference connections belong on a compact converter board; J2 is a
logical prototype boundary, not approval for a long cable carrying raw ADC pins.

## Scope of the checks

```sh
python3 -m hardware.electronics.adc_driver.generate
python3 -m hardware.electronics.adc_driver.verify --kicad-cli /path/to/kicad-cli
```

Native KiCad10.0.7 ERC has zero violations. Independent contracts cover all79
component values/pins. Fresh exports match E10 and E09. The inherited E10
BUF_OUT bound is4.036Vrms before its passive output resistor; the E12 screen
reserves4.06Vrms at PRE_OUT. Gain is chosen to leave some margin to the ADC's
typical2Vrms differential full scale, including the listed DC allocation.
Actual ADC full scale and end-to-end unity gain still need calibration.

The exported-netlist model checks18 nominal AC cases,192 independent feedback
resistor/load corners,128 allocated DC cases and36 hypothetical finite-gain
sensitivities. Another512 resistor/reference corners use superposition to bound
ten independent DC error sources, including hot FDA/servo bias and offset.
The ADC load hypotheses are260Ω±15% per pin to ground,260Ω±15%
differential, and260Ω±15% per pin to reference/2. These bracket useful static
cases; they do not identify the actual codec input model. Remote feedback reduces
the dependence of audio-band gain on those loads but does not prove stability
against the real switched input.

The finite model is an assumed two-pole FDA plus common-mode loop and output
resistance. It checks audio-band sensitivity, **not gain/phase margin or
transient stability**. No manufacturer macromodel or ADC switching model was
run. Such verification must precede accepting the1pF compensation or PCB routing.

The own-circuit nominal20Hz–20kHz noise screen is1.35µVrms differential,
unweighted. It uses typical colored amplifier noise and resistor Johnson noise
with nominal matching. It excludes pump/rail noise, aliasing, reference dynamics
and other system stages. **The original98dB master/102dB send-return weighted
S/N targets are still open.** Published codec DNR includes its evaluation path;
do not double-count that path or treat this stage-only calculation as a system
noise approval. Noise optimization may require revising these provisional gains,
resistor values or the preceding stage after the complete budget is closed.

No E12 PCB, component/connector placement, thermal or enclosure clearance is
claimed. The current A03/E07 clearance record excludes E08–E12.

Primary sources: [THS4551 Rev.D](https://www.ti.com/lit/ds/symlink/ths4551.pdf),
[LM7705 Rev.D](https://www.ti.com/lit/ds/symlink/lm7705.pdf),
[OPA4192 Rev.E](https://www.ti.com/lit/ds/symlink/opa4192.pdf),
[OPA1656](https://www.ti.com/lit/ds/symlink/opa1656.pdf),
[BAT54S](https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf),
[ES9292PRO v0.1](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf).
See [dependencies.json](dependencies.json) for provenance and remaining allocations.
