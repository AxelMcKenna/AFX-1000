# Left ADC bias connection

The new 11.35 mm branch connects A_C114 pin 1 to the existing NBIAS_L network on the front and In2 copper layers through one 0.30 mm drill. Both layers use the same In1 ground reference. A short 0.04 mm offset in the adjacent bias trace preserves its return copper around the new via.

The native check measures both new trace segments against the connected ground plane and compares the adjusted bias trace with its original return coverage. Ground trimmed at the new via stays within 0.75 mm of the drill center. The report lists the affected area per layer and checks the remaining traces and nearby component pads. All other named pad groups retain their connectivity. KiCad reports 47 opens and the missing A_U201 codec footprint.

[Route and copper measurements](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
