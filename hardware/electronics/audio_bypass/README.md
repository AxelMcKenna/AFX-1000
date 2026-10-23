# E03 stereo bypass contacts

E03 is the native KiCad contact-side schematic for the standalone processor's
power-off dry path. It has two non-latching G6K-2F-Y DC5 relays and four prototype
interfaces. The [E02 circuit](../bypass/README.md) supplies the watchdog, latch,
coil driver and suppression. **There is no routed E03 PCB or assembled circuit.**

Open [the KiCad project](audio_bypass.kicad_pro),
[schematic SVG](generated/audio_bypass.svg), [BOM](bom.csv) or
[connection schedule](components.json). The
[native verification record](generated/verification.json) checks the exported
pin nets and E02 coil interface, not just the generator's intended connections.
The [combined E02/E03 review archive](../../releases/README.md#bypass-review-e03)
keeps both native projects and their checks together; it contains no production
fabrication files.

## Contact assignment

The [Omron drawing, page 6](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf)
shows the selected single-side stable relay from the top. Coil pin 1 is positive
and pin 8 is negative. Pole commons are 3/6, NC contacts 2/7 and NO contacts 4/5.
The G6KU latching variant and the through-hole bottom-view drawing are different
references and must not be substituted.

| Relay | Common pins 3 / 6 | Released, NC pins 2 / 7 | Energized, NO pins 4 / 5 |
| --- | --- | --- | --- |
| K1 output selector | Line output L / R | Line input L / R | Processed output L / R |
| K2 input isolation | Processing input L / R | Intentionally unconnected | Line input L / R |

Both coils are wired in parallel. Released K1 passes dry audio while released K2
disconnects the processing inputs. This avoids relying on unpowered amplifier or
converter inputs to remain high impedance. Audio returns remain continuous;
there is no galvanic isolation. This circuit cannot guarantee bypass if a relay
contact is welded or mechanically stuck.

The model also checks the two mixed settled states, since relay operation and
release are not simultaneous. In every checked state, dry and processed output
sources remain separate and left/right signals remain separate. These ideal
checks do not simulate contact travel, bounce, overlap, clicks or relay faults.

## Harness and analog boundary

| Connector | Pins in order |
| --- | --- |
| J1 line input | 1:Left, 2:analog return, 3:Right |
| J2 line output | 1:Left, 2:analog return, 3:Right |
| J3 analog stages | 1:processing input L, 2:analog return, 3:processing input R, 4:processed output L, 5:analog return, 6:processed output R |
| J4 coil driver | 1:regulated 5 V, 2:E02 switched low side |

Connect J4 to E02 J4 pin-for-pin using a suitable harness. The verifier freshly
exports the E02 schematic and checks both terminals, the MOSFET drain and clamp
polarity connections. E02 J5 remains reserved for the separate gain relays;
those contacts are not on this sheet. A plain coil flyback diode is not added
here because it would change E02's proposed release suppression.

J3 connects to the protected line-level analog input/output stages, not directly
to the Seed3 audio pins. Input-source selection/normalling for RCA versus TS
must happen upstream of J1, without joining two independent sources. J2's total
external load and any parallel output jacks remain the analog output stage's
responsibility. The input protection and gain networks are still incomplete.

The headers are prototype 2.54 mm footprint candidates, not selected production
connectors. Coil current returns through E02's digital/power return. Do not route
it through the analog return pins. The analog/digital reference connection and
shield treatment must be resolved in the complete carrier layout.

## Verification and remaining work

The verifier runs all-severity native KiCad ERC, checks the exact exported pin
contract, exercises four settled contact combinations and checks the actual
E02 coil interface. It also audits every relay land's number, center and size
against the manufacturer's top-view pattern: 7 mm between pad rows, with
3.2 / 2.2 / 2.2 mm column spacings and 0.8 × 1.8 mm lands. The standard library
footprint is rotated mathematically for this comparison; no board placement is
implied. This establishes the nominal land pattern, not physical assembled fit.

    python3 -m hardware.electronics.audio_bypass.generate
    python3 -m hardware.electronics.audio_bypass.verify --kicad-cli /path/to/kicad-cli

Run from the repository root with the sibling E02 schematic present. The
verifier accepts optional --footprint-dir and --driver-schematic paths. Checks
use isolated KiCad settings. No third-party footprint is copied into this repo.

Before fabrication, integrate these contacts with the actual protected analog
stages, connectors, rail monitoring, short suppression loops and PCB grounding;
then run full-board ERC/DRC/parity. The A02 audio-board outline is a placement
reserve and does not prove that this circuit and the analog stages fit.

On the bench, measure unpowered dry continuity, released processing-input
isolation, both channel gains, crosstalk, signal-level contact distortion,
hot-plug/DC transients, relay timing and clamp overshoot. Repeat power-loss and
watchdog/manual bypass tests with the complete unit. No physical measurement or
fabrication approval is claimed by this schematic.
