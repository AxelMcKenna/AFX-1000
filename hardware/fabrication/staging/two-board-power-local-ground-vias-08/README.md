# Local ground vias for monitor and protection passives

Forty-two previously isolated resistor and capacitor pads now have a short return to an adjacent, connected ground plane. Each uses a 0.30 mm surface trace and a dedicated through-via with a 0.60 mm land and 0.30 mm drill. Pad-center to via-center lengths range from 1.05 to 1.50 mm.

The added returns serve 20 rail-disconnect, six rail-monitor, nine negative-rail protection and seven fan-circuit pads. Each new land fits inside the adjacent connected ground fill, with clearance to the existing copper objects and foreign plane fills. The paths clear the enclosure contact regions. Component placement and board geometry match the enclosure capture.

KiCad confirms 42 intended pad-group joins and 1,788 remaining opens. Geometry and schematic parity checks pass on both the saved and fully refilled board. ERC retains the existing isolated-reference warnings at N_U19 and N_U24. The via geometry uses the provisional eight-layer board rules. Manufacturing drill tolerances, threshold noise and loaded electrical performance remain open.

[Connectivity](connectivity.json) · [Via and return geometry](return-review.json) · [Detailed paths](routes.json) · [Saved-board DRC](drc.json) · [Schematic ERC](erc.json) · [Retained objects](retention.json) · [Paired placement](placement.json) · [Previous revision](../two-board-power-monitor-returns-07/README.md)

A full refill preserves the physical pad groups. All 47 filled copper regions match the independently refilled preceding revision. [Refill comparison](refill-comparison.json)
