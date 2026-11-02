# AC04 — six-section audio main schematic

The input range, ADC driver, ESS codec, DAC receiver, output stage and sequenced
bypass are combined on **one proposed main PCB**. The circuit contains **329
electrical parts / 971 exported physical terminals** on six hierarchical sheets.
The isolated Linux KiCad 10.0.7 export has **zero ERC findings** on all seven
pages, with every category enabled. This project has **no PCB layout** and the
ESS U201 footprint remains unassigned.

The later [partial main-PCB candidate](../audio-main-placement-02/README.md)
places the 328 known electrical footprints and preserves the missing-codec
hold. This schematic source folder intentionally remains separate from that
unfinished PCB candidate.

Fifteen old headers are removed and two shared power headers added. Original
retained values, footprints and pin connections independently replay against
AC03 and the three selected input/output/bypass exports. Internal connections
now include the isolated input relay to preamp, preamp to ADC, DAC receiver to
output amps, output range to wet selector, both range-relay coils to their
common driver, and the analog-valid output to the bypass input qualifier.
No raw ADC/DAC, force/sense or driver-enable connection is exposed as a harness.

The master output amp uses protected **P19/N19**; its send/return amp and the
other analog stages keep **P12/N12**. Relay coils and bypass digital supervision
use protected **5V_DIG**, separate from **V5_REG**. The bypass logic shares the
MCU's **V3V3_IO** through J402.2. Those rail joins do not prove current capacity,
voltage at the loads, partial-power behavior or acceptable noise.

| Header | Pin order | Intended peer |
| --- | --- | --- |
| J701 | P19, AGND, N19, P12, N12, V5_REG | E28 J3, straight six-pin order |
| J702 | 5V_DIG, AGND | E28 digital force distribution, receiving/fanout unfinished |
| J402 | AGND, V3V3_IO, SCL, SDA, CODEC_RUN, ANALOG_OK, AGND, PRE_ANALOG_OK, CODEC_PGOOD, ANALOG_OK | Digital J1006 on pins 1–6; monitor J4 on pins 7–8; pins 9–10 unwired status |
| J403 | AGND, NBIAS_L, NBIAS_R | Monitor J3 |
| J203 | AGND, BCLK, WS, ADC_DATA, DAC_DATA | Digital J1005 |
| J602 | AGND, HEARTBEAT, MCU_PERMIT, GAIN_REQ, ARMED, BYPASS_SENSE | Digital J1003 |
| J606 | AGND, INPUT_READY | Digital J1007 |
| J603 | V3V3_IO, PROCESS_OK, ANALOG_OK, AGND, BYPASS_SENSE | Manual bypass; pin 3 unwired status |
| J607 | IN_L, AGND, IN_R | Rear input assembly, logical contacts only |
| J608 | OUT_L, AGND, OUT_R | Rear output assembly, logical contacts only |

J701 uses a captured KiCad land for proposed Molex **43045-0600**; J702 uses
JST **B2B-XH-A(LF)(SN)**. The [Molex family drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430450600_sd.pdf)
and [JST XH documentation](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf) are
manufacturer sources. The actual captured six-pin grid is [0,0], [3,0], [6,0],
[0,3], [3,3], [6,3] mm with nominal 1.02 mm signal drills. J702 has a 2.5 mm grid
and **1.0 mm** nominal drills. These native dimensions are verified; complete
drawing orientation, retention, hole/process tolerances, mating and placement
approval remain open. No approved crimp/wire purchasing list follows.

The [42-conductor, 11-bundle logical audio-leg proposal](audio-leg-connections.csv)
is checked against captured E28/monitor exports and the combined digital
placement. `peer-selection.json` freezes those sources for reproducible replay;
the current inventory separately compares all used peer headers' pin nets,
values and lands against the presently selected boards. The selected receipt is
`integration-handoff-03.json`; earlier receipts are historical. Every header
contact is accounted for, including three unwired
status contacts. It is **not** a completed manufacturing harness: rear and
manual-switch contacts are logical, E28 digital-force distribution to the other
loads is unresolved, and wire parts, splices, lengths, crimps, strain relief,
ground returns and SAI integrity require design and receiving checks.

**The former AC03 four-way power harness is incompatible.** AC03's separate
preamp/output/bypass and analog-valid links must not be fitted to this board.
Its individual development-board copper is not adopted by the integration.

The independent checker verifies exact joined audio/gain nodes and all four
ADC force/sense and raw-DAC terminal groups. It evaluates **16,384 coupled
powered Boolean cases**, including manual bypass retaining a qualified input
connection, gain transitions invalidating input-ready/wet enable, and startup
faults preventing wet enable despite stale timer states. These are static logic
checks: reset/latch edges, relay motion, analog loading, power ramps, fault pulse
widths and rapid rearm are not dynamically qualified. The earlier conditional
ADC request/DC and 1.2 s settling budgets replay with their existing limits;
the missing ESS electrical data and CT discharge/process assumptions remain.

```sh
python -m hardware.fabrication.audit_audio_main --check
python -m unittest discover -s tests/tooling -p 'test_audio_main_integration.py' -v
python -m hardware.fabrication.audit_scope
```

Use the AP01 **150 × 63 mm** audio allocation for placement. The exact ESS land,
all copper including physical force/sense joins, tall-film placement outside
the upper monitor, mounting/support details, analog gain/noise/stability,
coil-current returns, thermal and full current assembly/harness review remain
unfinished. **No fabrication release, supplier message, upload or order.**
