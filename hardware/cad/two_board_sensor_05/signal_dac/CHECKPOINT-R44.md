# R303 common-mode routing checkpoint

Selected electrical checkpoint: `native-r44/signal_main.kicad_pcb`, SHA-256 `8e9f3ec18176bc305237a59271691fbfd8b329f27040d016033ab40992fdfa67`.

This adds one CM_DRV_L connection to r26, reducing total native opens from 198 to 197. Seven DAC connections remain. R303 retains its 0805 footprint, orientation, and F.Cu side and moves from (120, 73) to (109, 82.5) mm. The other 476 component poses and every previously accepted track, via, authored zone, and board setting remain unchanged. R308's exploratory move was restored. The route adds three route pieces and two signal vias; both returns use existing ground vias.

Observed checks: native KiCad geometry/courtyard, ERC, exact netlist parity, independent 197-open capture, 66 new-reference cases, 4,877 retained-reference cases, 36 verified local returns, 183 polygon fidelity cases, 56 drill cases (minimum 0.102145 mm), and fail-closed transition identity regressions. The native capture preview was inspected. Missing A_U201 (ES9292QPRO) remains the original parity finding.

The reference policy is unchanged. Raw retained losses remain visible: IV_P_L 0.0174405523 mm² attributed to its physically contacted, return-verified transition and native boundary band; RX_OUT_L 0.0000579392 mm² within the native boundary band. No unexplained new or retained loss is accepted. New-via planning conservatively reserves proven old return corridors by 0.64 mm: the existing 0.63 mm native knockout/pruning extent plus 0.01 mm planning margin. Acceptance still uses the independent native fields and original limits.

Integration must refresh affected mechanical checks for the one explicit placement change before selecting this board for the housing assembly. This is not a fabrication release or noise/stability qualification. The ESS package remains unresolved; the other 190 non-DAC opens remain.

```sh
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r44 --reference --regressions
```

The portable command verifies local immutable source bytes and the declared component translation, recomputes reference evidence, and checks identity failures at their intended assertions without rewriting frozen artifacts. `final-review-r44.json` binds the complete source closure. Earlier failed probes remain unselected.
