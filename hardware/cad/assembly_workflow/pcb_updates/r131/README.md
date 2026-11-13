# R131 signal-board selection

R131 closes REF_HALF_L and REF_HALF_R with seven additive F.Cu tracks, reducing signal-board opens from 166 to 164. All 477 r125 footprint objects, prior authored copper/zones and native mounting rules remain unchanged. Root mechanical comparison finds no physical differences, so the cumulative r125 R303/R308/D101 capture remains current.

Root portable verification reproduced 135 introduced-route reference cases, 4,873 retained cases with their original identities, 67 return cases, 238 fill-fidelity cases and 99 drill cases. Three invalid transition mutations and the shared-directory/contract-integrity regression pass. All 147 assembly checks passed, and selected status confirmed all 83 roles at this checkpoint. The later main-fastener integration retains this board and the nine panel-input routes.

The D101/C105 0.02 mm receiving-envelope gap remains nominal-only; the nominal 0.625 mm B.Fab drawing gap is not a supplier/process tolerance guarantee. Missing ESS geometry, remaining routing, analog performance, physical assembly and fabrication qualification remain open. Selected power remains TBP73 at 1,936 opens.

Reproduce the electrical gate with `python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r131 --reference --regressions` from the repository root. This routing-only selection changes no housing dimensions or component placements.
