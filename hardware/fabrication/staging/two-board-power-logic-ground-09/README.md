# Comparator and controller ground returns

Six ground pins now connect to the adjacent In1 ground plane through short 0.30 mm front traces and dedicated 0.60 mm vias with 0.30 mm drills. KiCad confirms the six intended joins, taking the power board from 1,788 to 1,782 open connections.

| Circuit | Ground pins | Pad-center to via-center length |
| --- | --- | --- |
| Rail-disconnect comparators | E_U10 pin 12, E_U9 pin 12 | 1.50 mm, 1.80 mm |
| Rail-monitor comparator | M_U3 pin 12 | 1.80 mm |
| Negative-rail comparators | N_U15 pin 12, N_U14 pin 4 | 1.50 mm, 1.25 mm |
| ATtiny84A fan controller | F_U1 pin 14 | 1.25 mm |

Native DRC reports zero geometry and schematic parity findings on both the saved and fully refilled board. ERC retains two isolated-reference warnings. The board keeps all original footprint positions and mounting clearances. Supply distribution, operating noise, oscillator layout, bench performance and fabrication stackup remain open.

[Pad-group connectivity](connectivity.json) · [Via and return geometry](return-review.json) · [Routes](routes.json) · [Saved-board DRC](drc.json) · [Schematic ERC](erc.json) · [Retained copper](retention.json) · [Paired placement](placement.json) · [Previous revision](../two-board-power-local-ground-vias-08/README.md)

A full refill preserves the physical pad groups. All 47 filled copper regions match the independently refilled preceding revision. [Refill comparison](refill-comparison.json)
