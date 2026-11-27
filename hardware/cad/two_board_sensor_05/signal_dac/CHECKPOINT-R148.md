# Signal checkpoint r148 — PD_R with exact authorized detours

From accepted r139, closes the remaining modeled PD_R connection. Native KiCad reports 162 opens, zero geometry/ERC violations, exact netlist partitions and unchanged missing-ESS parity. The new signal route is 6.396428 mm: a front escape through (75.8,77.65), then an In3 join to the existing PD_R via at (80.5,79.5875). Its new LINK_AGND return at (74.5,76.65) has a directly verified 1.640122 mm corridor on In1/In4/In6. Two explicit adjacent ground patches provide the required reference.

Exactly three authorized non-feedback objects are replaced. All endpoints, nets, native groups and widths are preserved:

| Original object | Width | Original length | Replacement length |
|---|---:|---:|---:|
| V5 `b1c1865b-7772-58be-ab73-298eb697dc74` | 0.6 mm | 1.600000 mm | 2.925061 mm |
| INPUT_ENABLE `094cfe15-e54e-5a1a-86f3-64eb7dd586b8` | 0.2 mm | 3.701351 mm | 4.652494 mm |
| BIAS_WINDOW_OK `e278094b-72b0-5e04-90d5-578081219fd8` | 0.2 mm | 3.401470 mm | 4.401470 mm |

All other authored copper/zones, FDA feedback geometry, all 477 footprints, mount keepouts and native rules remain unchanged. The cumulative gate verifies 141 introduced route cases, 4,871 unchanged original reference identities, and the exact two retired original cases mapped to their fully referenced replacement tracks. It also checks 68 returns, 241 raw/unfractured zone cases and 101 drill cases. The exact replacement audit is authoritative for the three removals; inherited native report prose about preserved originals means all other originals, as its declared-removal list specifies.

The patch audit retains raw gained/lost field witnesses. Tiny In1/In4 boundary gains are attributed only to exact unchanged authored LINK_AGND polygons within the source-bound local patch projection/contact area, within the native 0.005 mm boundary limit and outside original keepouts. This is not a global numerical waiver: unrelated gains, remote losses, net merges and moat bridges remain rejected. The two raw triangle witnesses and zone UUIDs are preserved in patch-audit-r148.json.

Rejected r146 is retained: native electrical checks passed, but its upper INPUT_ENABLE dogleg lacked 0.005865 mm² of reference. r148 moves that upper dogleg 0.05 mm right while preserving the lower via-avoidance path and endpoints. All replacement/reference checks now pass without removing that requirement.

No new physical placement is introduced. Root must rebind the selected PCB/capture and mechanical checks using the cumulative r125 poses. The inherited 0.02 mm D101/C105 receiving gap remains nominal-only. Missing ESS, 162 remaining opens, analog/noise/stability, manufacturing tolerances and fabrication release remain open.

Reproduce: `.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r148 --reference --regressions`.
