# PD_L FDA escape checkpoint r125

This bounded electrical candidate completes the modeled PD_L connection to A_U101 pin7, reducing native opens from 167 to 166. It changes A_D101 from B.Cu (75,66,0°) to B.Cu (75.8,65.2,90°), preserving its footprint, package, nets and pad identities. Exactly its two original GND/V5 stubs are replaced to follow the moved pads; their remote endpoints, nets, widths and layers remain fixed. Every other r107 authored object, including all hardware keepouts and the companion native rule file, is preserved.

The new signal via is (75.925,65.575), with a front escape from (77.1125,65.675), then In3.Cu to the existing PD_L track. Physical In4 reference copper and In4/In6 local-return corridors are added. The existing ground return via at (74.8125,67.57) is retained. Exact length, native group membership and all transformed pad coordinates are in `replacement-audit-r125.json` and `transitions-r125.json`.

A_D101's courtyard bounds change from [73.07,64.3,76.93,67.7] to [74.1,63.27,77.5,67.13]. The native pose was serialized in pinned Linux KiCad and checked against independently transformed world-pad positions. The physical-pose audit captures all 477 footprints and permits only the cumulative R303, R308 and D101 moves relative to input-r7. Root must generate a fresh cumulative CAD capture and run the complete affected assembly checks before selection. This checkpoint does not assert housing acceptance.

Run:

```
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r125 --reference --regressions
```

Required electrical gates: native geometry/ERC/netlist parity; independent 166 opens; exact two-stub/one-footprint delta and only one PD_L cluster merge; 133 cumulative route-reference cases; 4873 retained original reference cases; 67 local returns; 238 raw-zone fidelity cases; 99 new/replaced drill checks. Original feedback geometry, sensitive-node exclusions, reference tolerances and return requirements are unchanged. The count of retained reference cases remains 4873: the replaced original ground stub was excluded by policy, and the replaced V5 stub had no originally covered reference case. Its replacement is explicitly screened as a new route.

Failed candidates are preserved. r117's simple 0.5 mm translation overlapped A_C103's courtyard. r123's legal rotated placement completed the connection but its proposed via removed original NBIAS_L reference coverage. r125 moves the via within the measured access region and preflights a conservative 0.63 mm ground-pruning envelope against existing covered front traces. Native full reference verification remains mandatory; the preflight is not an acceptance substitute.

The existing missing ESS footprint, 166 remaining opens, noise/stability/crosstalk qualification, fresh mechanical integration and fabrication release remain unresolved. The selected root board stays r107 until integration accepts this exact candidate.
