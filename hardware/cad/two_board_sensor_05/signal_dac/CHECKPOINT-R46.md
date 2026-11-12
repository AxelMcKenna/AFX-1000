# Buffer input routing with physical ground reference

Verified electrical checkpoint: `native-r46b/signal_main.kicad_pcb`, SHA-256 `b14fdbcf427dc996a97a2aa4971011f3e9ede6cb18f88de36f9c07dc3eb44eb6`.

This connects BUF_IN_L, reducing total native opens from 197 to 196. Six DAC connections remain. Every r44 component pose, track, via, authored zone, keepout, and board setting is retained. R303 remains at its declared r44 location; no further component moves are introduced.

The addition comprises two front-side escapes, an In3.Cu connection, two signal vias, and one ground stitch. One actual LINK_AGND zone beneath the internal route and two small In6.Cu return zones extend the reference copper. These use the accepted r24 construction: 1.2 mm route-corridor radius, 0.7 mm return-corridor radius, and the unchanged native clearance/minimum-width settings. Existing exclusions remain untouched. The filled native copper—not the proposed outlines—is checked for main-ground continuity and reference support.

Observed validation: native geometry/ERC/exact netlist parity and 196-open captured cross-check; 69 new-reference cases; 4,877 retained-reference cases; 38 exact-identity local returns within 2.5 mm; 186 raw polygon fidelity cases; 59 drill checks with minimum 0.102145 mm clearance; fail-closed identity regressions. The native-capture route preview was inspected. All unexplained reference loss is below the existing acceptance threshold; raw IV_P_L and RX_OUT_L changes remain explicitly accounted under the unchanged policy.

The full portable check is:

```sh
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r46 --reference --regressions
```

`final-review-r46.json` binds immutable sources, local Python imports, native evidence, and exact project inputs. Integration must refresh selected-PCB/capture identity and affected mechanical evidence. Relative to r44, physical package poses and board outline/stackup are unchanged. Six DAC opens, 190 other opens, missing A_U201 (ES9292QPRO), and noise/stability/fabrication qualification remain unresolved.
