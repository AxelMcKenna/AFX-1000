# Added-part schematic association correction

This isolated metadata candidate starts at `main_ldo/native-03`, not selected TBP73. It adds the exact schematic UUID path to 18 previously added electrical footprints, including P_C906. All 1,086 older electrical paths already matched. The 15 mechanical footprints have no electrical symbol and are explicitly board-only. P_C907 belongs to the separate unfinished `ldo_local` experiment and is not present in this source; its path must be included when that experiment is resumed.

The complete board AST is unchanged after removing only footprint path nodes. Native KiCad additionally proves all original copper objects, fills and connectivity groups unchanged: 1,943 opens remain. Source schematic files and PCB/symbol library contents are hash-bound. Relative library links must resolve inside this worktree.

The UUID gate is separate from schematic-to-PCB update safety. Native `--schematic-parity` reports **18 existing footprint-symbol identifier mismatches**: board assembly variants use `AUX_ROUTE`, whereas schematic fields still name standard footprints or are blank. These must be reconciled before promoting a schematic update. The four TPS3703 DSE 0.15 mm clearances remain unwaived against the 0.20 mm rule. No manufacturing or functional qualification is claimed.

`native-01` preserved an initial library resolution mistake: it linked schematic libraries instead of the source PCB libraries, causing 18 extra missing-library warnings. `native-02` corrects only that target and retains the original 18 schematic parity warnings and four DSE errors. Neither run saves or changes the candidate board.

Checks:

```
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.associations.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.associations.test_paths
```

Five mutation tests cover the path-only delta, wrong existing path, duplicate reference, missing old association and unexpected electrical reference. Self-review identified the separate footprint-ID round-trip issue; it remains an explicit promotion blocker, not hidden behind native command exit success.
