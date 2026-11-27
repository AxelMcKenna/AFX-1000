# Repaired C13 complete receiving candidate — staged

Root reproduced the isolated C13 repair verifier and four mutation tests. An initial test invocation used the wrong module path and failed before tests ran; its log is retained separately. The corrected test command is `python -m unittest tests.tooling.test_aux_c13_receiving`.

This stage binds exact candidate board 52619e87e2069c78f8fc232152165859b0591913fa667b5a059058d2c6a87be3 and keeps the previous 32-part receiving budget: manufacturer package maxima, 0.25 mm XY allowance per side, 0.5 mm height allowance, complete courtyard coverage, and no reduction of existing component allocations. E_C13's original box moves intact to [105.795,125.895,107.755,129.295], Z [9.14,11.36]. Host full-peer comparison now has no E_C13 conflict and retains the two unresolved C907/U102 and L900/N_U22 witnesses.

The complete external native screen has not yet run for this corrected board. It is staged behind the live selected-assembly runtime revalidation to avoid competing cache jobs or changing the active selection. Power remains TBP73. Process tolerances, electrical/thermal performance and manufacturing remain unqualified.
