# Local AUX bypass connections

This candidate connects the supply pins of N_U32 and N_U10 to nearby 100 nF capacitors through two 0.30 mm front tracks, two 0.30 mm rear tracks and two 0.60 mm vias with 0.30 mm drills. The rear tracks meet existing AUX copper attached to the capacitor terminals. The capacitor and IC ground pads already belong to the main ground group.

| Supply pin | Capacitor | Added trace length | Supply via to connected ground via |
| --- | --- | ---: | ---: |
| N_U32.5 | N_C88.1 | 3.171 mm | 1.011 mm |
| N_U10.5 | N_C3.1 | 1.642 mm | 1.082 mm |

KiCad 10.0.7 reports 1,913 uncapped open connections, down from 1,915. The named pad groups match the two expected joins. Both the full refill and saved board pass geometry and schematic parity checks. The native DRC lists up to 499 open markers. [Connectivity](connectivity.json) · [Saved board DRC](drc.json) · [Full refill DRC](refill-drc.json)

The new traces have adjacent ground-plane coverage up to the supply via clearances. Both nearby return vias contact the connected In1 and In6 ground fields. Only those two ground fills changed. The other 45 zone-layer fills retain their original geometry. Board outlines, mounting holes, component positions and physical footprint geometry match the assembly capture. [Return geometry](return-review.json) · [Retained copper](retention.json) · [Placement comparison](placement.json)

These are local bypass connections. Both supply pins still require a connection to the AUX regulator. The loop impedance, loaded rail behavior and fabrication stackup remain unqualified.
