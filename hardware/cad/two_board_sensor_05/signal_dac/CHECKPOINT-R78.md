# RX_POS_R connection with a verified layer transition

Electrical checkpoint: `native-r78/signal_main.kicad_pcb`, SHA-256 `e7a80a398d8c65ff0009a7df98f769eef6f42ea47b48d5074a67df1b21cf4527`.

RX_POS_R is connected, reducing native opens from 192 to 191. BIAS_P_R is the sole remaining DAC connection. The earlier CM_SUM_L and CM_DRV_L connections are restored after replacing exactly eight agent-added objects: two vias and six segments. Every original track/via, every retained r62 authored object, all 477 current footprint poses and all r62 native groups are preserved. The exact removed and added inventory is recorded in `replacement-audit-r78.json`.

The added closure path is 45.086564207314034 mm: F.Cu 2.911745 mm, B.Cu 8.735433 mm, In3.Cu 7.028500 mm and In5.Cu 26.410885 mm. These lengths exclude previously accepted RX_POS_R branches. An intermediate through-via at (123.938867, 70.945894) mm switches In3 to In5, with its actual local ground return independently verified. The batch adds five signal vias while removing two, no ground vias, and four physical In4/In6 LINK_AGND reference zones. No new layer roles or footprint translations are introduced.

This route is longer than the straight endpoint separation. Its closest foreign same-layer copper is CM_SUM_L on In3, with 0.2131428 mm measured edge separation. The source-bound context report lists the closest same-layer objects and adjacent-layer projected foreign copper, including A__P12 near the In5 route. Those geometric measurements and reference coverage are not analog-noise, stability or crosstalk acceptance. Any later shortening must retain the same native, reference and return requirements.

Observed checks: native geometry/ERC/exact schematic parity and independent 191-open capture; 85 new-reference and 4,877 retained-reference cases; 47 local returns; 202 polygon-fidelity cases; 71 drill cases with minimum 0.102145 mm clearance. Nineteen focused tests cover signal-via identity, sensitive exclusions, bounded return/visibility/grid searches and original-versus-reworkable copper. The native capture preview was inspected.

The first native-clean bridge had a 0.000001051258 mm² uncovered area beside a neighboring BIAS_N_L via. Moving only its new In5 departure resolves that finding. No reference tolerance or exclusion was enlarged. The failed witness and provisional open-escape states remain distinct from the accepted board.

```sh
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r78 --reference --regressions
```

The portable entry point recomputes the exact replacement audit, final gate and full reference review; its mutations reject missing, wrong-net and missing-intermediate-via return evidence at the intended assertions. Root integration must select the new board/capture identity; component poses remain identical to r62. The missing ESS footprint finding, 190 non-DAC opens, the last DAC connection and full analog/manufacturing qualification remain unresolved.
