# R308 routing and transported sensitive-pad exclusion

Electrical checkpoint: `native-r62/signal_main.kicad_pcb`, SHA-256 `11cf6e9b94c5460793d040e85b81714b511b517c93fce2a82452b9bc576a4fe4`.

IV_P_L and RX_NEG_L are connected, reducing native opens from 194 to 192. Two DAC connections remain: BIAS_P_R and RX_POS_R. Both R308 pads are now connected. R308 moves from (116, 68) to (120.5, 81) mm on F.Cu; its package, orientation and all other footprint geometry stay unchanged. The prior R303 translation remains the only other change from input-r7. All accepted r50 tracks, vias and authored zones remain fixed.

R308 pin 2 belongs to the original sensitive RX_NEG_L net. Its native pad geometry, translated before route planning and buffered by the original source rule of 0.5 mm, defines one additional In1/In2 copper-pour exclusion. The old openings remain fixed. This 4.378674 mm² opening is independently checked against the source pad and actual native rule area; it is not a route-wide exemption. The reference report separately exposes its contribution. Noise/stability qualification remains outstanding.

The batch adds five route pieces, three through signal vias and five actual ground reference zones, using existing ground vias. A 0.1 mm widening of only the newly added In4 corridor removed a native copper-sliver warning. A local In5 bend avoids an existing foreign-net via's ground opening while preserving copper clearance. The new return-path search adds a finite V-shaped family; every accepted path still requires native ground coverage, exact signal/return identity, 0.2 mm corridor width, at most 2.5 mm length and the same 2 nm numerical allowance.

Observed acceptance evidence: native geometry/ERC/exact parity and independent 192-open capture; 79 new and 4,877 retained reference cases; 44 local returns; 198 raw-zone fidelity cases; 68 drills with minimum 0.102145 mm clearance. The final gate also checks all 477 footprints, exact board settings and original authored zones, allows only the declared new keepout, and binds source files recursively.

```sh
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r62 --reference --regressions
```

The transported exclusion accounts for 0.169542 mm² of new surface copper; no unexplained new or retained reference losses remain. Seven regression tests passed. The final native preview was inspected.

Root integration must refresh mechanical capture/allocation for the R308 translation and rerun affected fit checks before selecting this board. The original missing ESS footprint finding, 190 non-DAC opens and full noise/stability/manufacturing qualification remain unresolved.
