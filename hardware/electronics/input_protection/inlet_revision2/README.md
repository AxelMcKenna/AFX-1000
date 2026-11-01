# E23I2 passive rear inlet for P03

This separate five-component variant preserves the original rear jack, logic switch, relieved outline and four mounting holes. It replaces the original E23 input/protection board **only together with the complete P03 guard/supply replacement**. Connecting P03 through the original 3 A E23 guard would preserve an incompatible current limit.

The center-positive PJ-102AH jack feeds a 6 A backup fuse and a keyed JST VH connector. The switch carries auxiliary logic only. Its positions connect POWER_RUN to SWITCH_SUPPLY or AGND. The actual P03 input guard provides normal electronic current limiting; the fuse alone cannot enforce the jack's 5 A catalog limit or prove fault clearing. The external adapter and complete fuse/jack/cable/guard fault coordination remain unqualified.

| Interface | Pins | Connection |
| --- | --- | --- |
| J2 B2PS-VH(LF)(SN) | 1 DC_IN, 2 AGND | P03 raw input; VHR-2N, SVH-41T-P1.1 contacts, AWG16 |
| J3 B3B-XH-A(LF)(SN) | 1 SWITCH_SUPPLY, 2 POWER_RUN, 3 AGND | P03 auxiliary/run interface; logic only |

The [JST manufacturer drawing](https://www.jst.com/wp-content/uploads/2025/06/eVH.pdf) gives 10 A with AWG16, an approximately 10.5 mm mated side-entry height and 20.5 mm depth before wire bend. Bare-header size is insufficient for enclosure integration. Its catalog contact resistance is orders of magnitude above the quiet-return joint allocation; this connector is for the 12 V inlet. Actual crimping, harness routing/strain relief, mating accessibility, plug/jack heating and assembly tolerances require review and measurement. The original jack/switch footprint process approval is not inherited from a native DRC pass.

```sh
python3 -m hardware.electronics.input_protection.inlet_revision2.generate --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.inlet_revision2.check --kicad-cli /path/to/kicad-cli
```

The two-layer native PCB declares an explicit candidate stackup. Power trunks are 3 mm, with short 1.2 mm fuse-terminal necks; only the logic paths use vias. Independent checks bind the exact jack/fuse/connector/switch pin contract and actual copper paths. The conditional copper-only resistance/loss calculation excludes contacts, fuse, pads, holes and wires and cannot establish a complete path or temperature bound. Fabricator acceptance and physical qualification are pending. No fabrication or power-up release is granted.
