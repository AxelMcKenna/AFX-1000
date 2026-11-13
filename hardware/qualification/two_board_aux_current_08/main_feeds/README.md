# Rejected feed candidates and workflow diagnostics — design held

**Neither `native-01` nor `native-02` is accepted as an electrical PCB checkpoint.** The latest verified isolated board remains `../precision/native-01` (`b5e33ad7`), with 1945 opens and 49 fills. The accepted TBP73 board is unchanged. Further design passes were held at the user's request to prioritize the workflow interface; all running bounded operations finished before this evidence checkpoint.

The screen found a 0.3 mm main-LDO feed separately, but it did not coexist with the candidate VIN feed in either bounded route order. No claim of impossibility is made. VIN candidate `plan.json` uses the existing source via at (193.2,117.8), a new ground-return via at (194,117.6), and 16 B.Cu tracks. Return separation is 0.824621 mm, with positive-area actual In1/In6 reference contact. Its 0.183712 mm² reference exception is confined to the exact captured single-VIN-via In6 antipad; this is not a general permission to route without reference. Pairing and loop impedance are not electrically qualified.

Native `native-01` retained all prior objects, 49 fills and only the declared connectivity joins, giving 1944 opens, but DRC found **seven new track-to-B.Cu-zone clearance errors** in addition to the four unwaived DSE errors. Root cause: the original routing screen omitted same-surface filled zones. `routing_zones.py` now supplies a tested obstacle gate: foreign fills block routes unless their exact IDs are declared for cutback; keepouts cannot be waived this way. The helper is not yet wired into the parent repository's general manifest interface. `transition_dc_avoid.py` uses it and rejected the bounded route while preserving DC_IN.

`native-02` tests a deliberately declared native refill of only the two touched B.Cu zones. Native DRC returned to the original four DSE errors and native connectivity stayed unchanged. **The stricter local-delta verifier still rejects it:**

| Zone | Removed copper | Removal outside declared 0.202 mm new-copper clearance envelope |
|---|---:|---:|
| AGND `bc76c316…` | 0.859866 mm² | 0.001512 mm² |
| DC_IN `da7a2424…` | 1.639095 mm² | 0.273200 mm² |

Neither zone gained copper; each stayed one connected polygon. That alone does not qualify the current path. The DC_IN region contacts P_D101.1 and eight existing vias, so a broader cutback permission was not granted. Native source-zone minimum thickness is 0.25 mm, but removal extends as far as approximately 0.640419 mm from the added copper in DC_IN; it was not silently attributed to rounding or waived. The original authored route, rejected DRC, native full refill, retained-zone output, exact deltas and bounded process logs are retained for review. Scratch `native-02/refill/` is unnecessary and uncommitted.

An unimplemented diagnostic alternative identified a return-via site near the other VIN via (188.95,125.3), but it would require an explicit antipad in In2 PWR_MODULE_FEED_IN. No new geometry or refill was started for it before the hold. This is not a selected design.

The exact r31 cradle keepouts from harness commit `c39e0d3b` are copied as `contact-keepouts.json` (SHA256 `9975b35aeb05140e87408b99d9f373c6a69588591cfa4eadfdf03cddad577d4d`). Existing and added surface copper checks preserve them. Captured H_NEW5 NPTH geometry is its drill, not a copper pad; the check only excludes an unnetted NPTH whose captured size matches its drill. Mechanical pressure/insulation/abrasion remain conditional.

Run `python -m unittest hardware.qualification.two_board_aux_current_08.main_feeds.test_zones hardware.qualification.two_board_aux_current_08.main_feeds.test_diagnostics`. Passing tests mean the obstacle rules work and both failed native candidates remain rejected, **not** that this PCB is qualified. `verify.py` without its diagnostic flag and `verify_fill.py` are intentionally expected to fail on their respective rejected candidates. Self-review identified and retained the filled-zone planning omission and the excessive native fill delta; neither finding was suppressed.
