# Startup logic placement and interconnect plan

Candidate plan from TBP40, not a fabrication release. U29/U40 and their existing
100 nF bypass capacitors move together, without changing parts or pin nets.
The prior U29 VCC escape is enclosed at the planned track/via clearances.

The first fanout template angled away too early beside neighboring IC pads and
placed the larger C74 pad too close to another via. The corrected template
runs straight beyond the pad ends and offsets the capacitor. It passes the
unchanged copper/drill screens in all four orientations for both IC/package
combinations. The full-board search also screens courtyard/body/tail reserves.

All eight pins of each IC have screened surface/via reservations. The current
interconnect plan restores both U29 master-enable pins and connects the three
U40 PG inputs, three Schmitt outputs, U29 FOLLOW1 output, AUX_VALID input and
two AUX supply branches. U29 ALL_RAILS_ALLOW remains reserved but unconnected;
its unused via/trace must not be emitted. Two fixed gate input escapes are
included. Source-driven input connectivity still depends on the other logic.

Ground and reference copper, native DRC/ERC/parity, connection-preservation,
quiet-return ownership and visual checks remain required. The scratch search
programs retain temporary paths; plan.json is the construction input. Geometry
screen results do not establish electrical timing, noise or thermal limits.
