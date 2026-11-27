# Digital I/O supply connection

The MCU 3.3 V output group at D_U1001 pin 38 now connects to the A_R201 pin 2 group on LINK_V3V3_IO. The 48.07 mm connection uses 0.50 mm copper on In3.Cu and B.Cu and one 0.60/0.30 mm via. Native connectivity leaves 55 opens. The via adds local clearance at the 5 V digital plane edge. The copper comparison preserves a 1 mm wide semicircular path around the via and every original 5 V contact. The supply current budget and loaded voltage remain to be verified. The ES9292QPRO footprint is pending.

[Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

## Supply loading

The new trace feeds the analog-board section from Daisy Seed pin 38. KiCad connects the 27 digital-section pads to all 63 placed analog-section pads. The schematic also assigns codec A_U201 pin 30 to this rail. That pin still lacks a physical land.

The analog section has two 1 µF and nineteen 100 nF bypass capacitors to ground, totaling 3.9 µF nominal. Charging those capacitors from 0 to 3.3 V on a linear 1 ms ramp would require 12.9 mA from the supply. Its eight resistor branches draw at most 4.73 mA in aggregate at 3.3 V if each sees the full rail voltage and each resistance is 1% low. Active ICs, oscillator A_Y201 and loads attached to A_J402 or A_J603 add to those figures.

For the added 48.07 mm trace, 0.50 mm finished width and 35 µm copper on both routed layers give approximately 47 mΩ at 20 °C, or 4.7 mV per 100 mA. This calculation covers trace copper only. Finished copper thickness, via resistance, source impedance and loaded voltage still require confirmation. The Seed3 datasheet identifies pin 38 as an output and gives no external-load current rating. The older 1 A allocation applies to the Seed input. [Seed3 datasheet](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed3/Daisy_Seed3_datasheet.pdf) · [Power budget provenance](../../a12/thermal/power_budget_audit/README.md)
