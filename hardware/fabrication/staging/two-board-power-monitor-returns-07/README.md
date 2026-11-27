# Rail-monitor and fan-circuit ground returns

Forty previously isolated capacitor and resistor ground pads now connect to 29 existing plated ground contacts. Thirteen pads serve the rail-monitor circuit, and 27 serve the fan circuit. The 47 added front-copper traces are 0.30 mm wide. Their paths range from 1.03 to 5.98 mm. None adds a hole. Native KiCad connectivity confirms the 40 intended joins, taking the power board from 1,870 to 1,830 opens.

Each trace lies over the connected In1 ground field, and its destination contact joins that field. The paths clear the enclosure contact regions. The schematic, footprint placement, board settings, original copper objects and 47 saved zone fills are preserved. DRC reports zero geometry and schematic parity findings. ERC retains two isolated-reference warnings at N_U19 and N_U24.

Five monitor returns share one existing ground contact. The four 100 pF filters and one divider resistor on that contact still need a noise and threshold-accuracy check. F_C20 and F_C21 now have ground returns. Their crystal-side placement and oscillator performance remain under review.

Refilling preserves every physical pad group. All 47 saved and independently refilled copper regions match the preceding revision. [Refill comparison](refill-comparison.json)

[Native connectivity](connectivity.json) · [Trace lengths and contacts](return-review.json) · [Routes](routes.json) · [Saved-board DRC](drc.json) · [Schematic ERC](erc.json) · [Retained copper](retention.json) · [Paired placement](placement.json) · [Previous revision](../two-board-power-local-monitoring-06/README.md)
