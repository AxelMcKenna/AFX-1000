# Digital I/O supply connection

The MCU 3.3 V output group at D_U1001 pin 38 now connects to the A_R201 pin 2 group on LINK_V3V3_IO. The 48.07 mm connection uses 0.50 mm copper on In3.Cu and B.Cu and one 0.60/0.30 mm via. Native connectivity leaves 55 opens. The via adds local clearance at the 5 V digital plane edge. The copper comparison preserves a 1 mm wide semicircular path around the via and every original 5 V contact. The supply current budget and loaded voltage remain to be verified. The ES9292QPRO footprint is pending.

[Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
