# Analog-control construction plan 05

This plan supplies native candidate 02. It reuses the twelve native component
poses from `two-board-analog-cell-native-poses-04`, including reversed R100,
and short local quiet returns from plan 04.

`revise-routes.py` preserves the shared U31/U14 enable backbone at (34.8,132)
and removes two redundant U13 vias whose connections stay on F.Cu. The exact
retained objects and omitted vias are recorded in `routes.json`. The independent
geometry screen passes. `zone-search.py` constructs seven owned quiet regions;
the separate U32 capacitor reference field connects through its explicit quiet
stitch to the In1 field and then the pin-8 star.

The resulting [native candidate](../two-board-power-analog-cells-native-02/README.md)
has clean native geometry/parity, all intended joins and valid quiet ownership,
but six reference gaps remain. This plan is not selected or fabrication-ready.
Keep its bound inputs and successful scripts unchanged; use a new plan version
for the next correction.
