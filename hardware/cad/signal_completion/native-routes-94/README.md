# DAC serial data link

A_J203 pin 5 reaches D_R1014 pin 2 and D_J1005 pin 5 on LINK_DAC_DATA. The 72.60 mm route uses 0.20 mm copper on F.Cu, In2.Cu and In3.Cu, three signal vias and two ground stitching vias. KiCad verified continuous ground coverage on In1 or In4 along every segment after accounting for the signal-via and terminal clearances. The two stitching vias connect the ground references within 1.91 mm of their signal vias.

The In2 digital 5 V pour remains a single connected region. At 96 mA per header on the 0.065 mm mesh, the largest modeled increase among the four header drops is 0.014 mV. The route runs alongside LINK_ARMED for 14.74 mm within a 0.60 mm edge gap. DAC timing and coupling still need bench verification.

KiCad reports 32 open connections, zero geometry violations and zero ERC findings. A_U201 remains absent from the layout pending the ESS package drawing.

[Route geometry](route.json) · [Ground coverage](reference-review.json) · [Digital supply model](power-sheet.json) · [Adjacent traces](coupling.json) · [Native connectivity](native-review.json) · [Paired board geometry](placement.json) · [DRC](drc.json) · [ERC](erc.json)
