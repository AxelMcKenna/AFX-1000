# E05 circuit / E07 routed stereo output board

E05 is the native KiCad schematic for the post-receiver line drivers and stereo
gain-output relay: 41 components, fixed-feedback master/consumer amplifiers,
separate coupling/bleed networks and the E02/E03 interfaces. E07 is a **routed,
unassembled output-stage prototype**, not the complete analog/power design.

The [native E07 PCB](output_stage.kicad_pcb) is 82 × 34 × 1.6 mm with four copper
layers, 211 track segments and 45 through vias. The
[routing check](generated/routing-verification.json) passes all-severity native
DRC/library/parity with **zero violations and zero open connections**. KiCad
refills and saves the analog reference plane before the check. Native
[top](generated/placement-top.svg), [bottom](generated/placement-bottom.svg),
[reference plane](generated/reference-plane.svg) and
[inner routing](generated/inner-routing.svg) views show the actual saved board.
This electrical layout check does not establish fabrication readiness or audio
performance; final stackup, passive/connector selection and bench work remain open.

Open [the native project](output_stage.kicad_pro),
[schematic SVG](generated/output_stage.svg), [BOM](bom.csv),
[connection schedule](components.json) or
[verification record](generated/verification.json). The
[circuit analysis](generated/circuit-analysis.json) uses the actual exported
netlist and explicitly identifies its ideal-device assumptions.
The [A03/E07 review package](../../cad/generated/standalone-review-A03-E07.zip)
includes the current hardware sources, native projects, CAD and check records.
Standard KiCad/OpenSCAD and the documented Python packages remain external.

## Circuit and boundary

J1 requires a low-impedance, nominal 2 V RMS full-scale **single-ended** signal
nominally centered on 0 V after the DAC's I/V and differential receiver/filter.
It is not an interface to the raw codec differential pins. The
[E08 receiver prototype](../dac_receiver/README.md) proposes a ±25 mV DC
allocation and checks that allowance against the E05 peak-margin screen. The
original ideal E05 calculations use zero DC; physical scale, calibration and
power behavior remain unverified. Keep its source impedance
at or below 100 Ω; R17/R18 provide 100 kΩ bias returns.

Both drivers run continuously. U1, OPA2992D on regulated ±19 V, supplies Master
gain 6.23 using 5.23 kΩ/1 kΩ feedback. U2, OPA1612AID on regulated ±12 V, supplies
Send/Return gain 1.605 using 1.21 kΩ/2 kΩ feedback. The consumer resistor scale
keeps the feedback and output loads together above 2 kΩ. Feedback stays connected
regardless of the gain relay position.

Each branch has 100 Ω series resistance, two parallel 4.7 µF nonpolar film
capacitors and a 20 kΩ discharge resistor. K3 selects Master through its NC
contacts or Send/Return through its NO contacts; it never directly joins the
two amplifier outputs. Separate coupling networks let both branches retain
their own DC settling. Capacitors block DC in the ideal model; leakage,
dielectric behavior and switching transients require measurement.

| Interface | Pins / connection |
| --- | --- |
| J1 post-receiver input | 1:Left, 2:AGND, 3:Right; 2 V RMS nominal full scale, zero DC |
| J2 processed output | 1:Left, 2:AGND, 3:Right → E03 J3 pins 4/5/6 |
| J3 gain coil | 1:5 V, 2:GAIN_LOW → E02 J5 pins 1/2 |
| J4 regulated supplies | 1:+19 V, 2:AGND, 3:−19 V, 4:+12 V, 5:−12 V |

The second gain relay, for stereo input-range selection, is external and must
share E02's gain driver as planned. Firmware D9 stays low for Master and high
for Send/Return; the existing dry-wait/gain-settle/rearm sequence still applies.
This sheet does not contain a second driver or another flyback clamp.

**All four analog rails** must qualify E02 ANALOG_OK, independently of firmware.
Loss of the ±12 V pair can invalidate the selected consumer output and receiver
even if ±19 V remains healthy. Exact supervisors, thresholds, sequencing and
power-down margins remain unselected. Use the digital/power return for the coil
current; resolve analog reference and shield connections in the integrated PCB.

±12 V gives the low-voltage receiver/driver domain room for the prospective ADC
driver; its final load remains to be calculated. This choice does not approve
the complete analog power budget. OPA1612 must not use the ±19 V rails.

## Calculated results and limits

With nominal parts, an ideal 2 V RMS input and a combined external 10 kΩ load:

| Result | Master | Send/Return |
| --- | ---: | ---: |
| Output at 1 kHz | 12.276 V RMS | 3.163 V RMS |
| Scale error against E01 target | −0.0050 dB | +0.0008 dB |
| Effective amplifier resistive load | 3.244 kΩ | 2.177 kΩ |
| Passive coupling loss at 20 Hz relative to 1 kHz | −0.0674 dB | −0.0674 dB |

The 20 kΩ bleed and the external load are both included. Tolerance analysis
enumerates all 64 sign combinations per branch, 256 total: 0.1% feedback/ground,
1% series/bleed and 10% for each coupling capacitor. At a fixed 10 kΩ external
load, calculated scale error stays within 0.022 dB, the passive 20 Hz coupling
loss stays below 0.084 dB and the amplifier load remains above 2 kΩ.

These are output-stage calculations. Receiver scale/loading and the full unit's
gain error are not verified. The 10 kΩ limit is the **combined** external load
of all parallel output connectors; smaller loads need a new review.

The rail screen includes 1% supply tolerance, worst feedback tolerances and a
1% high full-scale input. It leaves about 0.68 V of peak margin for Master with
an assumed 0.3 V amplifier rail reserve. That reserve is from OPA2992's 40 V/2 kΩ
table; its use at the planned 38 V supply is still a screening assumption.
The consumer screen uses OPA1612's 0.6 V reserve at 2 kΩ. Neither establishes
real clipping, distortion or capacitive-load stability.

The illustrative white-density output-noise estimates are approximately
6.88 µV RMS for Master and 0.89 µV for Send/Return over 20 Hz–20 kHz, unweighted.
They include passive coupling and bleed noise but omit 1/f noise, receiver/source
noise, supplies, PCB coupling and part spread. Do not combine these directly
with A-weighted codec figures or claim a passing whole-unit S/N result.

An ideal class-B/quiescent-power screen gives approximately 0.26 W for the
master dual package and 0.29 W for the consumer dual package. Reference thermal
resistances imply substantial temperature rise; actual board copper, airflow,
internal ambient and temperatures remain to be measured. There is no validated
short-circuit or overload rating for the output resistors or complete stage.

## Capacitors and housing impact

The reviewed WIMA MKS2 drawing is revision 03.26. It lists
MKS2C044701O00KSSD, 4.7 µF/63 V/10%, with a 7.2 × 11 × 18 mm nominal body,
5 mm lead pitch and nominal 0.5 mm leads. Each branch uses two in parallel for
9.4 µF. The earlier 10 µF/50 V part is absent from this current drawing and is
not used in E05. The [source record](dependencies.json) captures the PDF hash.

The standard footprint's actual 5 mm pitch and 0.8 mm drill are checked. Its
nominal plan size is a candidate; maximum body/lead tolerances, standoff,
courtyard and printed assembly still need fit checks. Its generic 3D model does
not prove the 18 mm height. The former A02 12 mm audio reserve did not contain
these parts. A03 now uses the E07 placement packet, lowers the board to Z=3.8,
adds a floor recess and staggers the capacitor pairs to clear scene controls.
The [CAD report](../../cad/generated/solid-validation.json) records empty
intersection with the modeled shell/controls, including switch-lead and
scene-PCB allowances. This remains conditional on the documented dimensions
and assembly limits, with physical fit unverified.

The [actual-PCB mechanical packet](generated/placement.json) includes all 41
component and 29 through-hole solder/lead reserves. The four series resistors,
four bleed resistors and C8 sit on the back. Trim through-hole protrusions,
including solder, to ≤1.5 mm. Qualify the underside resistor/capacitor height
limits and the remaining generic passive MPNs before assembly.

Four Ø2.4 mounting holes match the CAD's Ø7.2 bosses and Ø3.2 through bores for
CNC Kitchen M2 × 3 inserts. Through bores accommodate the short boss stack; the
insert is flush, with M2 × 4 board screws. The floor recess leaves 1.6 mm of
plastic. Actual bore/insert fit, wall/floor stiffness and screw engagement remain
physical checks. The converter/input and final power-board placements are open.

## Native checks and remaining integration

Routing is explicit in [route.py](route.py). Feedback stays on the top layer
near the amplifiers; the four coupled branches stay separate until K3. R10
moves down to avoid taking its ground pad across the consumer-left feedback
path. F.Cu/B.Cu carry most audio traces, In1.Cu is the AGND reference plane,
and In2.Cu carries the inputs, supply trunks, a short output crossing and the
separate two-wire coil circuit. Coil current returns only through E02's driver.
The routing uses 0.3–0.6 mm tracks and Ø0.7/0.3 mm through vias, with a 0.25 mm
minimum clearance. No blind vias, via-in-pad assembly process or buried vias are
required. The fabrication house's actual four-layer materials and copper weights
are still to be selected; the present 1.6 mm thickness is a mechanical contract.

Local bypasses follow the amplifier supply pins. The longer signal paths,
single reference plane, return currents, supply impedance, thermal behavior and
coil switching still require review and measurement on the assembled board.
Native DRC does not verify signal integrity, stability, S/N or switching clicks.

    python3 -m hardware.electronics.output_stage.generate
    python3 -m hardware.electronics.output_stage.place --kicad-cli /path/to/kicad-cli
    python3 -m hardware.electronics.output_stage.route
    python3 -m hardware.electronics.output_stage.verify --kicad-cli /path/to/kicad-cli
    python3 -m hardware.electronics.output_stage.check_placement --kicad-cli /path/to/kicad-cli
    python3 -m hardware.cad.standalone

The verifier runs all-severity native KiCad ERC and checks every exported pin
against an independent contract. Fresh E02/E03 exports confirm the harnesses.
A complex nodal solver checks both channels and both relay states at 20 Hz,
1 kHz and 20 kHz: 12 ideal AC cases, with four further ideal DC-blocking cases.
The analytical gain/filter expressions are compared against that circuit solve.
The checks do not run a semiconductor SPICE model or measure real crosstalk.

Standard libraries remain external; --footprint-dir can locate them. Source and
library hashes are recorded. Generation replaces the native schematic, so
persist circuit edits in generate.py while using this workflow.
Persist footprint positions and board datums in place.py. It regenerates the
board and overwrites direct PCB edits. route.py adds/replaces generated copper;
it accepts both the initial legacy file and KiCad 10's normalized saved file.
check_placement.py refills/saves the actual board, requires all native DRC/parity
and connectivity results to be clear, and exports the mechanical packet;
standalone.py rejects
a packet whose PCB hash is stale. Standard footprints are embedded in the PCB
as in a normal KiCad board; their external libraries are not vendored. The local
mounting footprint is original project geometry. For a deliberately placed-only
intermediate, check_placement.py --unrouted retains and reports open connections;
it cannot label that state as routed. The earlier placement-drc.json is retained
as historical E06 evidence; routing-drc.json is the current native result.

Complete the converter/receiver, stereo input protection/range stage, regulators,
all rail supervisors, final connectors, ESD and integrated PCB before fabrication.
Then measure frequency response, calibrated gain, noise/THD, clipping, DC/clicks,
hot-plug, capacitive loads, output shorts, power loss and actual temperatures.
Prototype header footprints, some passive MPNs and capacitor bias curves remain
selection gates. E07 routing is complete for this output subassembly. No board
has been ordered, fabricated, assembled or released as the complete unit.

Primary sources: [OPA2992](https://www.ti.com/lit/ds/symlink/opa2992.pdf),
[OPA1612](https://www.ti.com/lit/ds/symlink/opa1612.pdf),
[WIMA MKS2](https://wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf),
[Omron G6K](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf).
