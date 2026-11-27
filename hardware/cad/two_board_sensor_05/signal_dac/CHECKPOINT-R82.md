# DAC routing checkpoint r82

Closes the last modeled DAC connection, BIAS_P_R: 191 → 190 native opens overall, zero modeled DAC opens. The missing ESS footprint remains unresolved and this is not fabrication or analog acceptance.

The 32.26150372576409 mm added BIAS_P_R path uses two short front escapes and In5 copper referenced to physical In4 ground corridors. Two signal vias and one ground via are added; both new signal transitions have independently verified local returns. Three earlier agent-added In3 segments are replaced by local detours on BIAS_P_L and RX_POS_L. Original copper, all other r78 authored objects, and all r78 groups remain intact; exactly the two BIAS_P_R groups merge. No footprint pose changes occur. Historical R303 and R308 translations remain declared.

Candidate r81 exposed equal-priority intersecting ground zones. It is retained as failed evidence. r82 changes only the new corridor priorities to distinct 6000-series values, then reruns native fill and all gates. No clearance or reference tolerances change.

The final gate binds native geometry/ERC/parity, independent native connectivity, exact replacement inventory, 49 local returns, 205 raw-zone fidelity cases, 74 new/replaced via drills, all new and retained reference cases, and the source closure. The replacement audit records complete path lengths and nearest same-layer/adjacent projected foreign copper. Neither projected distances nor geometric coverage establish noise, stability, or crosstalk performance. These remain explicitly unqualified.

Run `python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r82 --reference --regressions` with the repository environment. Verification remaps only the recorded owner-root prefix, checks local hashes, and leaves frozen evidence unchanged. Root integration must confirm mechanical capture freshness before selection.
