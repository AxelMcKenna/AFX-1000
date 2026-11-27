# Buffered-reference routing checkpoint r131

Seven additive F.Cu tracks complete the modeled REF_HALF_L and REF_HALF_R joins inside the ADC reference/servo network, reducing native opens from 166 to 164. The routes are 11.031493 mm and 6.61 mm respectively. No existing copper, footprint, authored zone, via, mounting keepout, native rule, outline or stackup is changed. The two buffered outputs remain subject to the source E12-R2 reference, leakage and coupled-loop qualification requirements.

```
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r131 --reference --regressions
```

Required gates cover native geometry/ERC/netlist parity; independent 164 opens and exactly two native group merges; all existing authored objects and all 477 poses unchanged; 135 cumulative route-reference cases; the same 4873 retained-reference identities; 67 local returns; 238 fill-fidelity cases; 99 new/replaced drill checks relative to input-r7. The previous four native hardware-keepout rejection tests are inherited only because the complete rule file and all rule areas remain byte-identical. No new vias or reference zones are added.

The initial finite surface families were blocked. A bounded reference-domain path supplied the left detour; the right path uses a short interior dogleg. The selected lengths and clearance/reference constraints are explicit; neither route length nor geometric validity establishes analog loop stability, RF impedance or noise acceptance.

Physical poses are identical to r125. Its source-bound physical capture retains exactly the cumulative R303/R308/D101 moves. Root integration has identified only 0.02 mm between the D101 and C105 receiving/courtyard envelopes. That is nominal non-overlap, not a qualified placement tolerance. Native Fab drawings imply a larger nominal body gap, but their margins are not supplier maximum-body/process guarantees. r131 does not improve or waive this inherited condition.

The missing ESS footprint, remaining 164 opens, analog/noise/stability qualification, assembly placement tolerance and fabrication release remain unresolved. Root controls final selection and assembly status; this checkpoint only qualifies the bounded electrical geometry.
