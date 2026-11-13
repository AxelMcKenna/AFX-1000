# D_H4 conductive mounting clearance checkpoint r107

This checkpoint reroutes the two LINK_SDA front tracks outside the conductive D_H4 receiving disc and shifts the LED39 through-via from (189.2,77.8) to (189.2,77.5). Its two attached inner tracks are recentered on that via. Exactly five original copper objects are replaced; every other authored object and all 477 footprint poses are preserved from accepted r98. All electrical partitions remain unchanged at 167 opens.

The SDA detour is (190.5,85.1) → (191.394049,84.558567) → (188.5,68.9), 16.968978 mm. A new ground via at (188.45,77.0) and physical In4/In6 ground corridors supply the moved LED transition. The existing adjacent In1 plane is retained. Exact native return validation is mandatory.

Nine non-sensor-owned signal mounts receive native F.Cu track/via/pour rule areas and companion copper-pad disallow rules. The full radius 2.4 mm receiving envelope derives from DIN433 maximum washer OD 4.5 mm plus the project's maximum 0.15 mm registration. The frozen source is `hardware/cad/assembly_workflow/verification/main-fasteners-r1/`. A 2 nm outward guard prevents coordinate rounding from undercutting its polygon. Sensor-owned D_H2/D_H5 are untouched.

Only round NPTH pads entirely contained within their drill dimensions are exempt from the native pad rule; these contain no bearing-surface copper. SMD/PTH pads and NPTH copper annuli remain prohibited. The independent portable audit also checks actual front copper against every complete source region.

KiCad rule semantics use documented `Pad_Type`, `Pad_Shape`, `Size_X/Y`, `Hole_Size_X/Y`, `intersectsArea`, and `disallow pad`: https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html . Four isolated native negative tests restore conflicting track/via copper and introduce SMD/NPTH-annulus pads. Each must produce `items_not_allowed` for the exact mutated UUID.

Run the portable frozen verification from any checkout:

```
.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r107 --reference --regressions
```

Gates cover native geometry/ERC/netlist parity, independent 167 opens, all r98 partitions and authored objects, 130 cumulative introduced-route reference cases, 4873 retained original reference cases, 66 independently proven returns, 236 raw-zone fidelity cases, and 98 new/replaced drill clearances. The four removed original tracks are replaced by separately screened new paths; their obsolete geometry is not counted as retained. Reference tolerance and source-sensitive exclusions are unchanged. The newly excluded LED39 transition is bound to its exact native UUID/net/position/group and verified return. No diagnostic exclusion is treated as analog acceptance.

Failed r104 is preserved: blanket pad prohibitions flagged NPTH apertures, and the shifted via required its attached endpoints to be recentered. r105 passed native/reference geometry, then gained only the 2 nm outward guard in r107. Two regression-harness runs failed on unsupported SWIG LSET constructors; r107 copies the actual layer set of an existing front SMD pad and completes all four tests. The r105 transition report initially lacked a derived distance field; its preserved preflight log records that reporting failure, corrected before acceptance.

Missing A_U201 ESS footprint, 167 remaining opens, analog/noise/stability qualification, fabrication release and integration selection remain unresolved. Root must integrate this exact PCB and updated `.kicad_dru`; the PCB alone is not the complete native enforcement artifact. No component pose change occurred.
