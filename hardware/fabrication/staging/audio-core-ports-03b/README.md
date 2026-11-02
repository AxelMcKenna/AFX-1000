# AC03 shared audio-board connectors

This 218-part successor consolidates AC02's duplicate power connectors and
removes its legacy external enable connection. All 211 retained components
have exactly the same values, numbered pin nets and footprints. Startup
buffers, bias qualification, CT requirements and the analog circuits remain
unchanged. Four probe pads provide internal control access.

Open [the portable KiCad project](audio_core.kicad_pro),
[native export](netlist.xml), [native ERC](erc.json),
[independent handoff](integration-handoff.json),
[27-wire audio-leg schedule](audio-leg-connections.csv), or
[connector/mating-part candidates](connector-parts.json).

## Defined interfaces

| Port | Function and pin order | Board connector candidate |
| --- | --- | --- |
| J401 | 1:+12 V, 2:AGND, 3:−12 V, 4:regulated analog 5 V | Molex 43045-0400, 2 × 2, 3 mm, right-angle |
| J402 | 1:AGND, 2:MCU 3.3 V, 3:SCL, 4:SDA, 5:CODEC_RUN, 6:ANALOG_OK to carrier, 7:AGND, 8:PRE_ANALOG_OK, 9:CODEC_PGOOD status, 10:ANALOG_OK to bypass | JST B10B-XH-A(LF)(SN), 10-way, 2.5 mm |
| J403 | 1:AGND, 2:NBIAS_L, 3:NBIAS_R to rail monitor | JST B3B-XH-A(LF)(SN), 3-way, 2.5 mm |

J101 remains the stereo preamp input, J203 the synchronous audio link, and
J302 the stereo receiver output. Raw converter ADC/DAC signals stay internal.
CHIP_EN and ADC_DRV_ENABLE no longer appear on any header. TP401 observes
ADC_DRV_ENABLE, TP402 CHIP_EN, TP403 PD_GATED, and TP404 AGND. These are probe
pads, not wire-attachment points for the former enable harness.

The analog-power and MCU/control connectors use different families and row
arrangements. The schedule gives the two ANALOG_OK destinations separate
connector contacts, so it does not require two wires in one crimp. Cavity 9 of
the J402 mating housing is unpopulated for the normal harness; CODEC_PGOOD
remains available for status/test access. Every other header terminal has one
specified peer endpoint. Cut lengths and wire routing are not assigned yet.

## Manufacturer and land inputs

Power mating candidates are housing 43025-0400 and four 43030-0007 contacts.
Control and bias mating candidates are XHP-10/XHP-3 housings and
SXH-001T-P0.6 contacts. A 22 AWG wire with insulation diameter no greater than
1.85 mm is the common candidate envelope; exact wire, crimp tooling, process,
retention inspection and installed temperature remain unqualified.

The manufacturer sources are the
[Molex 43045 drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430450800_sd.pdf),
[43025 housing drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43025/430250400_sd.pdf),
[43030-0007 contact listing](https://www.molex.com/en-us/products/part-detail/43030-0007),
and [JST XH family drawing/catalog](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf).
Manufacturer PDF text was accessible, but local downloads failed; no downloaded
PDF hash or completed visual drawing approval is claimed.

Pinned KiCad stock lands are captured with hashes. The independent audit
checks their numbered grids: Molex pins 1/2 at (0,0)/(3,0), pins 3/4 at
(0,3)/(3,3), with 1.02 mm electrical drills; JST pins run at 2.5 mm pitch with
0.95 mm drills. This records the library's component-side coordinates and is
not a cable-face drawing. Mating-face orientation, locking/retention holes,
body limits, board-edge restrictions, shroud access, wire exits, drilling
tolerances and assembly acceptance still require full drawing/receiving review.

## Validation and remaining work

Native offline Linux KiCad 10.0.7 reports zero ERC findings, with every category
enabled. All 634 numbered terminals match the intended circuit. AC02's 128
powered logic cases, six stale-timer fault cases and 4,096 DC corners replay.
The eight bundles/27 conductors match the current source-bound native exports
of the disconnect, carrier, rail monitor, bypass, input-range and output boards.
Regression cases reject raw input rails, 5 V in the logic domain, polarity/
channel swaps and repeated source contacts.

This is an audio-leg connection proposal, not a complete manufacturing harness.
Peer mating parts, complete-unit distribution/fanout, length, gauge, crimps,
strain relief, voltage drop, return impedance, signal integrity and physical
receiving remain open. In particular, do not reuse the old separate-board
`ADC-ENABLE`, `ADC-CODEC` or `CODEC-DAC` harnesses.

The codec's revisioned land drawing and analog limits, effective timer
capacitance/discharge, integrated audio PCB routing, actual force/sense pad
stars, enclosure/cooling integration and the rest of the complete-unit
fabrication package remain unfinished. No PCB DRC, mating geometry or physical
operation is certified. Earlier `audio-core-ports-03` reports retain the first
rejected label/grid construction and do not support this corrected candidate.

```sh
.venv/bin/python -m hardware.fabrication.audit_audio_ports --check
.venv/bin/python -m unittest discover -s tests/tooling -p test_audio_core_ports.py -v
```

The applied recipe is in `source-recipes/`; the constructor is
[`audio_core_ports.py`](../../audio_core_ports.py).
Original AC01/AC02 and peer-board sources are preserved. No Mac CAD application,
supplier message or order was used. Fabrication release remains false.
