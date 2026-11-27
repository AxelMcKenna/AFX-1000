# TBH05 custom AS5600 sensor PCB candidate

Use the checked project in `native-r3/`: `sensor.kicad_pro`, `sensor.kicad_sch`, and `sensor.kicad_pcb`. Root files are generator inputs; the native project has exported net codes and filled ground copper. Native KiCad 10.0.7 reported zero ERC, DRC, unconnected and schematic-parity violations, with no ignored checks. `visual-r1/` contains inspected front/back copper plots. This is an editable routed candidate, not a fabrication release or an assembled/powered sensor.

Board: 20 × 18 × 1.6 mm, two copper layers, no mounting holes. Carrier grips the empty perimeter. Populate the front with U1 AS5600-ASOM SOIC-8 and C1 Murata GRM188R71C104KA01D (100 nF, 16 V, X7R, ±10%, 0603). Confirm current purchasable manufacturer order codes before ordering. W1–W4 are plated solder-wire pads, not a purchased connector. Do not fit a header in their place. Use an assembly traveler to identify pin 1 and wire order; silkscreen labels are not present.

| Local pad | Local net | Signal main D_J1010 pin | Main net |
|---|---|---|---|
| W1 | AGND | 1 | LINK_AGND |
| W2 | V3V3_IO | 2 | LINK_V3V3_IO |
| W3 | SCL | 3 | LINK_SCL |
| W4 | SDA | 4 | LINK_SDA |

Pad order is increasing PCB X, at X 6 / 8.5 / 11 / 13.5 mm and Y 3.5 mm. View from the component/front side when using these coordinates. Verify continuity by net and pin, not by the apparent mirrored order from the back. Main pinout was read from `hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb`. Harness integration must bind its final chosen main-board revision.

This is 3.3 V I²C operation only: U1 pins 1 and 2 tie to V3V3_IO, pins 4 and 8 to AGND, pin 6 to SDA and pin 7 to SCL. OUT and PGO are deliberately unconnected. No OTP programming is permitted by this design; the OTP capacitor is absent. I²C address is 0x36. Pull-ups are not fitted here: verify the complete installed bus pull-up resistance, voltage and rise time before powered acceptance. The isolated board DRC does not establish bus operation or ground-noise immunity.

PCB front normal is world +X; PCB coordinate (x,y) maps to world (Y,Z)=(72+x,21.6+y). Substrate occupies world X299.7..301.3. U1 center is PCB (10,10), aligned to lever axis world Y82/Z31.6. Maximum modeled U1 top is X303.05. C1 population is limited to 1.0 mm including solder. Trim back wire tails and solder to ≤1.5 mm from the PCB back; front wire fillets ≤0.6 mm. Route wiring inside the carrier's documented wire reserve and provide harness strain relief. Header/body substitutions require a new fit check.

`../pcb_capture.py` extracts actual checked placements. `../population-contract.json` binds the PCB hash to conservative population geometry; `../population-verified-r1/review.json` verifies empty intersections with the carrier, shell, legacy control allocations and complete replacement lever/spring motion. Whole-assembly integration with the latest control carriers remains a separate check.

Assembly acceptance: inspect solder orientation/continuity, print and measure carrier, check smooth motion and endplay, then confirm magnetic detect/high/low flags and AGC throughout travel and temperature. Record zero/full-scale calibration and repeated return measurements. The magnet grade, adhesive and spring production/receiving gates in `../SPRING.md` remain open. No powered magnetic, fatigue, vibration or thermal qualification has been performed.

Design basis: [official AS5600 datasheet](https://www.infineon.com/assets/row/public/documents/30/49/infineon-as5600-datasheet-en.pdf), [manufacturer capacitor drawing](https://www.farnell.com/datasheets/2189124.pdf). These establish electrical configuration and package dimensions, not this assembly's performance.
