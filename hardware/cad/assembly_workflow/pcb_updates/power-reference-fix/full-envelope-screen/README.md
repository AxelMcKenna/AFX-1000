# Full affected power-part receiving screen

This diagnostic covers all 19 added parts and 13 changed-MPN parts in the immutable source09 power candidate. It uses manufacturer maximum dimensions from the verified package-envelope schedule, maps package axes through the native footprint rotation, and checks those axes against the footprint Fab rectangles. Actual board side is retained: 25 of the 32 affected parts are on B.Cu. The tallest new part, P_L900, occupies a receiving Z range of 3.3 to 8.1 mm below the power board.

The candidate receiving budget adds 0.25 mm per XY side, includes the complete courtyard, and adds 0.5 mm beyond maximum package height. The board-facing extent extends 0.2 mm into the substrate allocation for explicit seating overlap. These are provisional design allocations, not supplier-guaranteed solder, tilt, warp or placement tolerances. Existing envelopes for changed parts are retained as a union and never reduced; E_C13's existing envelope follows its verified rigid move. No selected component, board, rule or capture changes.

Eleven native checks cover the union of affected envelopes against 85 obstacle roles, including the unchanged peer allocations. Own power-substrate seating is excluded; all affected XY envelopes are explicitly clear of the signal substrate. All 32-versus-existing and 32-pair receiving-box overlaps are additionally calculated exactly on the host; this includes new-part mutual conflicts that the union-versus-external screen alone cannot detect.

The host witnesses are E_C13/E_C16 (2.2155045 mm³), P_C907/P_U102 (0.17457 mm³), and P_L900/N_U22 (0.648 mm³). They must be resolved by justified geometry/tolerance review or placement changes before promotion. The ongoing C907 westward-placement proposal is not included in this frozen candidate. No receiving conflict is waived or described as exact supplier-body contact.

The initial host builder incorrectly assumed newly added parts were front-mounted and stopped before creating a registry or launching CAD. `initial-side-assumption.py` preserves it; the corrected builder reads the actual layer and calculates front/back Z accordingly. Self-review checked all 32 identities/MPNs, source hashes, exact quarter-turn transforms, complete original envelopes, all peer pairs, external-role coverage and unchanged selected manifest. Full physical fit, electrical and thermal qualification remain open.

## Observed native result

Ten original groups pass; the final mixed group fails. Two additional localization checks retain identical geometry: unchanged peer allocations fail, while the remaining fastener/wire group passes. Thus all external housing, control, motion, fastener and existing-wire groups screened here are clear under this provisional receiving model; the three identified peer-envelope overlaps remain unresolved. The result does not qualify unmodeled wiring, process tolerances, electrical/thermal operation or full housing fit.
