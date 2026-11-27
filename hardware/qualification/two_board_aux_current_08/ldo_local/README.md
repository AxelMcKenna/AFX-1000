# Isolated main-LDO local bypass

Final candidate: `inputs-local-return-08/power_protection.kicad_pcb`. Its complete materialized schematic, footprint libraries and project context are frozen under this unique run directory and bound by `inputs-local-return-08.json`. This is not selected TBP73 and does not complete IN/EN source delivery or the held-rail design.

P_C907 is KEMET C0603C105K3RACTU, nominal 1 µF / 25 V X7R / 10%, at (187.5,126.6), F.Cu, 180°. Its positive pad connects to P_U102.8 through 0.809217 mm of 0.3 mm trace; its ground pad connects directly to P_U102.9 through 3.383580 mm of 0.4 mm trace. Four surface tracks, no vias, no existing part moved. The earlier 2.779 mm lead followed by 13.019 mm of existing ground chain is rejected as a short local bypass path.

The In1 main-ground patch is the explicit rectangle (186.7,127.8)–(188.0,130.8), 3.9 mm². Native fill contact is anchored to two original main-ground zones with 16 and four source-connected contacts respectively. All original native groups, quiet objects, copper and 55 full-identity anonymous pad mappings are preserved except the declared two new capacitor joins; opens remain 1,943. All original pads/tracks retain their reference copper, and new copper and conservative new pad rectangles clear both mechanical keepout sets.

The F.Cu AGND cutback is explicitly local, not a clearance waiver: source zone `d0572a8e-b95d-5c59-9a7c-1d3514a507b4`, first native corner-run replace 118:138 with 118:132. It removes 0.744739497 mm² within (187.69,125.95)–(188.57,127.65), adds none, preserves every old ground contact and leaves the other 48 source zones exact. Its thin native peninsula next to an old DC_IN antipad extends beyond a simple pad-clearance offset; the exact saved native corner-run and bounded rectangle are the review authority. Remote refill runs and the extra native polygon are rejected. Clearance rules are unchanged.

The selected-zone native interface loads/checks the whole board, builds connectivity, fills only the new zone, then imports only that fill. `failure-provenance.json` retains the prior 180 s full-board CLI timeout and the successful 2.16 s changed-workload diagnostic. The timeout's internal cause is not established. No unchanged failed operation was retried. `native-07` additionally had a new reference-text overlap; the final candidate changes only C907 reference size/position and checks exact board AST equality otherwise.

Schematic UUID and footprint identity are checked separately from net parity, including all 1,105 electrical parts and C907. Native command completion alone never passes the gate: the host manifest must match every native input byte, and recorded process hashes must match expected host hashes even when `inputs_unchanged` is true. This addresses the rejected `native-06` reused-path discrepancy without modifying a shared runner.

Qualification remains conditional. TI's hard input-capacitance minimum is effective 0.1 µF; the long-source 10 µF recommendation is not satisfied by assuming nominal 1 µF. The cached KEMET primary PDF page 2 bias curves are typical simulations, explicitly not specifications on page 4. Actual effective capacitance over voltage/temperature/age, the 39.247 mm input feed and existing remote C102 transient behavior, installed current/thermal performance, IN/EN routing and the wider reset/held-distribution gates remain open. Maximum capacitor body height is 0.95 mm; housing integration has not been qualified. Four TPS3703 DSE 0.15 mm clearances remain unwaived against the 0.20 mm rule.

Run the verifier and ten mutation tests:

```
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.ldo_local.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.ldo_local.test_verify
```
