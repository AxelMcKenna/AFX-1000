# Main LDO input-capacitor feed — isolated candidate

The 5 V source-connected group now has a proposed 0.3 mm B.Cu feed to P_C102.1: 15 tracks, 39.247145 mm, no vias. It starts on existing connected 5 V copper near (192.375,148.272001), not directly at the P_C901 pad. The native group audit explicitly joins the entire P_C901 source group to P_C102.1, with no other group change allowed.

`native-03` retains the original board except these tracks and a local corner cutback in B.Cu main-ground zone bc76c316-2c04-5ecb-85b7-3e5f80b26bf1. All other 48 zones, including every adjacent reference fill and DC_IN, remain exact. The saved ground removal is 0.76447936 mm², with no added ground. The local cutback envelope is explicitly 0.254 mm from new trace copper; its observed maximum removed-vertex distance is 0.252992317 mm. This is a bounded AGND corner revision using the actual native refill contour of a zone with 0.25 mm minimum thickness. The board's 0.2 mm electrical clearance is unchanged. It is not a permission for broader fill revisions.

`native-01` is diagnostic evidence. Full refill introduced two remote point-run changes in the same zone. `local_fill_exact.py` preserves those original runs and imports only the two local corner runs from the archived full refill. The four exact differing run ranges are asserted; a changed source fails. Native connectivity and DRC then validate the resulting saved board. No other zone is imported from the full refill.

Acceptance requires every original main-ground contact area retained, the exact declared connectivity merge, all original copper/pad identities unchanged, actual track reference coverage, quiet-copper exclusion, both cradle and 13 main-mount keepouts, and no additional DRC findings. The four existing DSE errors remain unwaived. The return plane is unchanged and there is no new layer transition in this step.

This does not yet connect P_U102 IN8 or EN5. They remain separate front-side islands. P_C102.2 and P_U102 GND4/EP9 already belong to native main ground. The capacitor center is about 8.87 mm from IN8, so a local input-bypass loop and paired transition must still be assessed. This route does not establish the conditional 20 mV held-rail allocation, actual current bound, installed thermal performance or shutdown timing.

```sh
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.main_ldo.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.main_ldo.test_verify
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.main_ldo.render
```

Accepted TBP73 is unchanged. Parent review is required before any selection change.

The 0.254 mm envelope is a proposed new, explicitly reviewed local AGND change; it does not widen the previous 0.202 mm screen silently. The original screen rejects it. Retaining the source-native minimum-thickness corner contour requires the larger local envelope: its largest portion outside 0.202 mm spans only 0.095644 × 0.047072 mm at the old corner. All four original ground contacts must retain their full contact area. No adjacent reference fill changes.

The native-02 intermediate also exposed SaveBoard reserialization of prior exact hole bridges. The final builder restores complete original source zone records before applying the two local corner runs. Exact AST equality is required for all 48 untouched zones; native fill-state equivalence alone is insufficient.

Observed checkpoint: exact native merge 1944 → 1943 opens; independent verifier and four tests pass; actual track reference gap is zero; all four original affected-zone ground contacts retain full area; both mechanical contact audits pass. Self-review caught and fixed remote fill-vertex changes and untouched-zone reserialization; rejected inputs remain archived. Four DSE findings remain unchanged and unwaived.
