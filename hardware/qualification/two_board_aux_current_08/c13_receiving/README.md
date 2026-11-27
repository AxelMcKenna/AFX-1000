# C13 receiving-envelope repair — isolated candidate

Candidate `inputs-review-02/power_protection.kicad_pcb` SHA256 `52619e87e2069c78f8fc232152165859b0591913fa667b5a059058d2c6a87be3` moves only E_C13 from (108.275,129.095) to (106.775,127.595), retaining angle90°, exact MPN, pads and nets. Two owned bypass tracks are replaced; the existing ground via remains. Supply lead is2.55mm and ground lead0.225mm. This is a geometric/local-loop improvement, not an impedance or transient qualification.

Panasonic FR datasheet pp1/5, visually checked, gives EEUFR1V221 nominal D8×L11.5 with D±0.5 and L±1.5: maximum8.5×13mm. The original C16 receiving square already covers maximum diameter; it was not shrunk. The original C13 receiving box was translated intact. New receiving bounds [105.795,125.895,107.755,129.295], Z9.14..11.36 leave0.455mm to unchanged C16 box. All1940 peer allocations pass, retaining root's provisional .25mm XY/.5mm height budgets. Body-to-lead registration, tilt, board warp and assembly process remain unqualified. Root must rerun external housing checks against this exact candidate.

Native review:1943opens unchanged, exact original pad groups and unrelated pad identities preserved, zero schematic-parity defects, all50source zones retained, new track reference coverage passes. Only the four existing TPS3703 DSE clearance violations remain, unwaived. No accepted PCB selection changes.

The first native attempt exposed SWIG lifetime handling after deleting tracks through a temporary list. The corrected native script retains removed track wrappers in a dictionary, as established scripts do; rejected process and original script are preserved. Native saving also changed serialized bridged fill ordering. `retain_fills.py` restores every exact source zone AST; review02 verifies identical native fill hashes and reruns DRC on the final immutable bundle. This is not a generalized fill normalization or clearance allowance.

Checks:
```
python3 -m hardware.qualification.two_board_aux_current_08.c13_receiving.verify
python3 -m unittest tests.tooling.test_aux_c13_receiving
```
Four mutation/reference tests pass. Native evidence is retained losslessly as gzip; source capture is shared at `../ldo_feed/capture-02/capture.json`. Self-review found and corrected the serialized-zone preservation gap before handoff. Rejected source09 receiving evidence remains in the root mechanical checkpoint; this candidate does not qualify P_L900/N_U22 or the remaining IN/EN circuitry.
