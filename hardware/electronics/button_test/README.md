# B01 button test PCB

This is a passive **32 × 16 × 1.6 mm test board** for the
[guided button fit fixture](../../cad/BUTTON-FIT.md): one B3F-1000, two M2 holes
22 mm apart, and a two-wire/2.54 mm connector. It is not the full control PCB
and contains no audio or power circuitry.

Open [button_test.kicad_pro](button_test.kicad_pro) in KiCad. The schematic,
board, passive symbols and three footprints are local. Switch holes follow the
manufacturer's top-view 6.5 × 4.5 mm pattern with 1 mm drills. No original RMX PCB
was copied.

| Terminal | Connect |
| --- | --- |
| J1 pin 1, S | Logic input with 3.3 V pull-up, or continuity lead |
| J1 pin 2, G | Ground, or other continuity lead |

Upper switch pads 3/4 are Signal; lower pads 1/2 are Ground in the manufacturer's
top view. Confirm against the actual part before soldering. Pressing joins the
two rows. Do not wire these terminals directly across a power supply.

The [native record](generated/verification.json) captures KiCad ERC, all-severity
DRC, unconnected-pad check, schematic parity and exported pin nets. All have zero
issues at the recorded hashes. **Physical fit, assembly and button operation
remain untested.** These checks apply only to this small passive board.

Native exports: [top](generated/board-top.svg), [bottom](generated/board-bottom.svg),
[schematic](generated/button_test.svg). The
[drill template](../../cad/generated/button-pcb-drill.svg) includes a 32 mm scale
check; print at 100%. It is a prototype aid without drill compensation.

    python3 -m hardware.electronics.button_test.generate
    python3 -m hardware.electronics.button_test.verify --kicad-cli /path/to/kicad-cli

KiCad 10.0.7 was checked from the official read-only application image with an
isolated configuration. The verifier stops on any ERC/DRC violation and confirms
the exported nets contain exactly J1.1/SW1.3/SW1.4 and J1.2/SW1.1/SW1.2.

Generation replaces the generated board/schematic; make persistent edits in
the generator, or stop regenerating when continuing directly in KiCad.
No board has been ordered, fabricated or released for production.
