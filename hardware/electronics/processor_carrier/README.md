# E19 processor carrier — schematic prototype

This circuit connects the Seed3 processor, ten knob inputs, E18 control hub,
E09 converter and E11 bypass controller for the **standalone external-converter
firmware profile**. It also exposes interfaces for the planned LED, touch,
angle-sensor and SD boards. Those interfaces do not complete those boards.

The 76-part native KiCad schematic passes electrical rules checks with zero
violations. An independent verifier checks all 40 module pins, ten knob channels,
connector pin order against fresh exports of the other four board schematics,
and the current F04 firmware assignments. See
[verification.json](generated/verification.json) and
[connector-map.csv](generated/connector-map.csv).

**There is no E19 PCB layout or routing yet.** Its proposed 150 × 65 mm size,
front-slot processor position, socket stack and 2 mm E18 daughterboard shift
have not been applied to the released CAD review. Full electronics placement,
wiring, thermal behavior and physical fit remain unverified. This is not a
fabrication package.

The ten 10 kΩ linear pots use the module's analog 3.3 V output, a 1 kΩ series
resistor, 100 nF shunt capacitor and 1 MΩ bleed per ADC input. Digital 3.3 V and
analog 3.3 V remain separate; module AGND and DGND join on the carrier.
[Conditional DC/RC screens](generated/passive-screen.json) do not verify ADC
acquisition, leakage, accuracy, noise or the full supply budget. Passive MPNs
and capacitor effective values remain to be selected and qualified.

The 40-pad library pattern preserves Electrosmith's supplied KiCad geometry:
2.54 mm pitch, 15.24 mm between rows, 1.7 mm pads and 1.1 mm holes. The unmodified
source and MIT license are in `vendor/`. The proposed pair of
[SSW-120-02-G-S sockets](https://www.samtec.com/products/ssw-120-02-g-s) needs an
assembly-specific footprint check before layout approval. Samtec's
[single-row layout](https://suddendocs.samtec.com/prints/ssw-s.pdf) calls for
1.04 mm nominal holes; the retained 1.1 mm pattern is not an approved substitute.
The Seed3 module's own PCB hole dimensions are a separate matter from the
carrier socket holes. Legacy module graphics/3D models are not a Seed3 fit proof.

J1 matches E17 J4 directly: pin 1 protected `5V_DIG`, pin 2 ground. It must not
receive raw 12 V. J6 requires a split harness: pins 1/2 feed E09 J4 pins 2/3;
pins 1/3/4/5/6 connect E09 J5 pins 1/2/3/4/6. E09 J4 pin 1 (`V5_REG`) comes from
the analog supply, not J6. Never join the module's 3.3 V outputs to a separate
regulator output. J2 reset and J4 bypass use the documented E18 signal aliases.
All E19 wiring is external-profile only; the onboard bring-up profile assigns
several of these processor pins differently.

Run from the repository root with Python 3.11+ and KiCad 10:

```sh
python3 -m hardware.electronics.processor_carrier.generate
python3 -m hardware.electronics.processor_carrier.verify --kicad-cli /path/to/kicad-cli
```
