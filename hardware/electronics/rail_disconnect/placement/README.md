# E25 rail-disconnect placement candidate

Physical continuation of the existing 164-part E17/E21 schematic. This separate directory preserves the circuit snapshot and the verified main-supply PCB.

The proposed 156 × 45.25 × 1.6 mm PCB has six proposed copper layers, fourteen MOSFETs in six opposing banks, six floating gate drivers, the independent OV/reference interlock and all six protected bulk capacitors. Four Ø2.4 mm M2 fixing holes are included. Electrical routing, loss/current distribution, fault timing and thermal performance remain unfinished.

The proposed housing datum is (8,108.5,4.6) mm, in the front strip below the existing controls. This is a placement proposal, not a fit result. The relieved PCB corners clear the existing case bosses. C20/C24 have moved away from the front control supports. A11 adds a local guide/inner-ledge relief for the C24 vent allocation; its separate native CAD report owns the conditional fit result. Header/harness and component heights remain allocations.

Bulk dimensions include the [Panasonic FR-A drawing](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf): D ±0.5 mm, L ±2 mm for the 20/25 mm bodies and L ±1.5 mm for 11.5 mm bodies. A further 0.41 mm seat/board allocation is retained. A11 allocates 2 mm of vent air using the [Panasonic application guidance](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/ABA0000C818.pdf). Physical vent operation and assembly remain unqualified. The driver and MOSFET references remain [Si8751](https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf), [CSD18540Q5B](https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf) and [CSD18510Q5B](https://www.ti.com/lit/ds/symlink/csd18510q5b.pdf). Package grouping is checked; stencil/process, leakage and isolation performance are unqualified.

From the isolated project root:

```sh
python3 -m hardware.electronics.rail_disconnect.placement.generate --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.rail_disconnect.placement.check --kicad-cli /path/to/kicad-cli
```

The checker requires original independent circuit/net/value contracts and native all-severity nonrouting DRC/parity, and reports real open connections. It does not suppress routing errors to call this a completed PCB. Rebuilding invalidates old placement evidence. No fabrication or power-up approval follows.
