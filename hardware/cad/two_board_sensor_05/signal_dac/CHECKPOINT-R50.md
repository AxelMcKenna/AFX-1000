# Left bias and right common-mode sum routing

Verified electrical checkpoint: `native-r50/signal_main.kicad_pcb`, SHA-256 `d07f63d33884878fef24149d03c4969d6c2d31f2a42d9dee122e173fd4d65f45`.

BIAS_P_L and CM_SUM_R are connected, reducing native opens from 196 to 194. Four DAC connections remain: BIAS_P_R, IV_P_L, RX_NEG_L, and RX_POS_R. R303 is now connected on both pads. Every r46 component pose and accepted track, via, authored zone, keepout, and board setting is preserved.

The batch adds five route pieces, three signal vias, three ground stitches, and five actual LINK_AGND reference zones. Left/right internal routes use In3/In5, with independently checked In4 reference. Local In6 ground corridors complete the through-via return checks. Existing sensitive-node exclusions and all acceptance thresholds are unchanged.

Observed checks: native geometry/ERC/exact parity and independent 194-open capture; 74 new-reference and 4,877 retained-reference cases; 41 local returns; 191 polygon-fidelity cases; 65 drill cases with minimum 0.102145 mm clearance; and fail-closed identity regressions. The native route preview was inspected. A stitch initially overlapped a same-net solder land; moving it to (117.55, 71.9375) mm and rebuilding its reference copper resolved the measured violation before acceptance.

```sh
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r50 --reference --regressions
```

The portable gate binds local Python dependencies and project inputs, checks the unchanged single R303 translation relative to input-r7, and recomputes immutable reference evidence. Selected-PCB/capture identity and affected mechanical evidence still require integration. No poses changed after r44. The original ESS footprint warning, 190 non-DAC opens, and full noise/stability/fabrication qualification remain unresolved.
