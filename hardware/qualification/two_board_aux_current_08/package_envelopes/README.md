# Candidate package envelopes

`envelopes.json` supplies manufacturer maximum X/Y/Z package bounds for all 19 additions and 13 changed-MPN references in corrected reference-09. It does not alter or promote the isolated power candidate. Dimensions follow the source drawing axes, not an inferred board rotation; transform using each actual footprint pose and drawing orientation. P_U901 conservatively includes its leads. These are package bounds rather than physical STEP-model accuracy claims.

Run from the repository root:

```
python3 hardware/qualification/two_board_aux_current_08/package_envelopes/verify.py
```

Every cached PDF and the exact candidate/BOM are hash-bound. TDK's two exact-part pages were read through the web tool on 2026-11-13; direct caching returned HTTP403. Their JSON records are explicitly transcribed observations, not cached manufacturer HTML. URLs allow independent reproduction. C3225X7R1C226K250AC currently says Production (NRND); no substitute was selected.

Maximum heights: P_L900 4.1 mm; P_C902/P_C905 3.1 mm; P_C901 2.8 mm; P_C900/P_C904 1.8 mm; P_U901 1.45 mm; all added KEMET0603 capacitors 0.95 mm; both supervisors and P_U900 0.8 mm; P_R902 0.7 mm. Existing changed KEMET0805 capacitors are 0.88 mm, PLT0805 resistors 0.8382 mm, and TNPW0805 resistors 0.55 mm.

Solder standoff, placement XY error, tilt and board warp remain explicit null process inputs. Null does not mean zero. A mechanical screening allowance may be chosen separately and labeled conditional; these sources do not qualify it. Do not silently replace the existing E_C13 housing envelope with a smaller nominal package code or treat package height as assembled height.

Self-review checked complete reference coverage, exact MPNs, upper tolerance arithmetic and source hashes. It corrected the T520 dimensional explanation to H2.8±0.3 rather than describing the calculated 3.1 mm limit as a quoted MAX row. All32 reference/source checks pass. This does not qualify housing fit, assembly tolerances, electrical current/thermal behavior or the four unresolved DSE clearance errors.
