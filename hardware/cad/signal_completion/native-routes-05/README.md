# DAC reference-buffer capacitors

A_C203 pin 1 and A_C204 pin 1 now share the REF_DAC_BUF node. The 3.05 mm trace runs on B.Cu over an 8.54 mm² ground pour on In6.Cu. Two existing plated ground vias tie the pour to the capacitor returns. The filled copper extends at least 0.32 mm past the trace edge along its length.

KiCad 10.0.7 confirms this is the only pad-group merge, bringing the signal board from 141 to 140 opens. Independently refilling the candidate and its parent preserves the original copper fields. Both saved and refilled layouts have zero geometry violations. ERC passes. Schematic parity reports the missing ES9292QPRO footprint at A_U201. Codec pin placement, reference noise and fabrication qualification remain open.

[Native connectivity](native-review.json) · [Trace and return geometry](reference-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-04/README.md)

Run the [reference verifier](../verify_reference_extension.py) from the repository root with KiCad Python.

```sh
python3 -m hardware.cad.signal_completion.verify_reference_extension hardware/cad/signal_completion/native-routes-04 hardware/cad/signal_completion/native-routes-05
```
