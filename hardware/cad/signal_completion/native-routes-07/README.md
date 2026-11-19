# Parallel output coupling capacitors

The resistor-side terminals of A_C501 and A_C513 now share the left series-resistor node. A_C502 and A_C514 share the corresponding right node. Each connection uses 9.953 mm of 0.25 mm copper on In3.Cu. Both routes reach their capacitor terminals through the component leads and use no signal vias.

Each route has an adjacent In4.Cu ground pour tied to system analog ground near both ends. At A_C502 pin 1, the signal pad and the nearby LINK_ANALOG_OK via share a clearance opening. Ground surrounds that opening and covers the full trace width beyond the signal pad clearance. The left and right copper additions clear the nearest mounting reserves by 38.24 mm and 16.44 mm, respectively.

KiCad 10.0.7 confirms the two intended joins, bringing the signal board to 136 opens. Independent copper refills preserve the geometry of all prior pours. Geometry and ERC checks pass. Schematic parity flags the missing codec footprint at A_U201. Analog performance and fabrication qualification remain open.

[Connectivity](native-review.json) · [Routes and reference geometry](reference-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-06/README.md)

Run the checks from the repository root using KiCad Python.

```sh
python3 -m hardware.cad.signal_completion.verify_output_returns hardware/cad/signal_completion/native-routes-06 hardware/cad/signal_completion/native-routes-07
```
