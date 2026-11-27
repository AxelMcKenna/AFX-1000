# Validity-signal pull-down returns

E_R143 on PWR_NF_OUTPUT_VALID and M_R114 on PRE_ANALOG_OK now have local ground returns. Each resistor uses a 1.35 mm long, 0.30 mm wide top-layer trace to a 0.60 mm ground via with a 0.30 mm drill. KiCad confirms both vias make copper contact with the In1.Cu ground plane.

The M_R114 via opens a 0.7915 mm² antipad in each DC input plane on In2.Cu and In3.Cu. Both planes retain a continuous 1.485 mm copper band around the opening. The independent refill confirms equivalent copper in the other zone layers.

KiCad 10.0.7 verifies both intended pad-group joins and 1,670 remaining open connections. DRC passes geometry and schematic parity. ERC retains the two isolated-reference warnings. Both placements match the assembly capture. Loaded rail behavior, installed fit and manufacturing verification remain open.

[Via and trace geometry](routes.json) · [DC plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-control-pulldowns-24/README.md)
