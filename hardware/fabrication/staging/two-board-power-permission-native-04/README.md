# TBP44 — startup permission and pull-up routing

Development checkpoint, **not ready for fabrication**. The power board has
**2,237 native open connections**, 30 fewer than TBP43. Signal remains at 251
opens with its approved ESS codec footprint missing.

U42 and its existing bypass capacitor C85 move together; U31 and C76 retain
their positions. Twenty-five targeted interconnects plus four main-ground
joins and one local bypass join close 30 connections. Seven complete control
nets now include ALL_RAILS_ALLOW, native AUX_VALID, NF_AUX_VALID,
NF_GLOBAL_MASTER, ANA_PG2, ANA_PG2_SCHMITT and E28_ANA_FOLLOW. All seven PG
pull-up AUX ends join the existing supply group. Pulldown returns and the
complete startup, supply and protection circuit remain unfinished.

The pass adds 183 tracks and 49 through vias and replaces one ANA_PG0 segment
with a short detour around the R95 supply projection. Current copper has
3,039 tracks, 435 vias, 39 zones and 2,975 native groups. All 1,101 footprints,
1,086 electrical parts and 3,420 schematic pin entries remain; two footprints
and ten pad positions move. Values, packages and schematic pin nets are unchanged.

## Verification

- Native geometry, schematic parity and ERC errors: **zero**. Two retained
  isolated-reference ERC warnings and 2,237 unrouted connections remain.
- [Independent review](permission-review.json): all 30 declared native merges,
  the restored ANA_PG0 connection and every other connection are verified.
- All **72 new or replacement non-ground route sections** have adjacent ground
  projection, with recorded same-net via and plated-pad antipad exclusions.
  This does not establish impedance, return inductance, timing or noise limits.
- **1,015 retained complete reference cases**, 22 own-quiet support sections,
  four star-only eFuse returns and all 33 fast-OV sections are preserved.
- The [retained-route review](retained-permission-reference-review.json) checks
  all 70 TBP43 route sections, including the restored ANA_PG0 detour. Earlier
  support coverage remains 24/28 and TBP40 startup coverage remains 7/15.
- The In4 source remains one connected field with all 20 contacts, now
  834.498043 mm². Its 1.712206 mm² fill change is explained by the declared
  vias and a [locked-AUX-via native control](../two-board-permission-source-diagnostic-02/README.md).
  Unexplained area is below 0.000001 mm². In5 uncovered source projection is
  approximately 0.349983 mm²; complete source-reference qualification is pending.
- Four main-ground outlines extend. Twenty-eight previous fills remain exact;
  eleven refill. Hole spacing, new-via drill-to-SMD and return ownership checks pass.
- [Net review](permission-net-review.json) records the seven complete control
  nets and seven pull-up supply joins. Electrical startup/fault behavior is unqualified.
- [Visual review](plots/visual-review.json): 19 current views directly inspected,
  including overlapping west/east details on all eight layers.

Candidates 01–03 exposed reference losses and an obsolete R119 branch. Those
findings were corrected through rerouting, a ground stitch and reuse of an
existing AUX via. The first isolated source test was rejected because its
unattached via inherited the ground net; the accepted second test locks and
checks AUX before and after filling. No clearance or quiet-return rule was waived.
The [construction plan](../two-board-permission-plan-04/README.md) retains the inputs.

## Current copper

[Front](plots/front.png) · [Back](plots/back.png) ·
[Six inner layers](plots/inner-contact-sheet.png)

| Detail | Front | Back | In1 | In2 | In3 | In4 | In5 | In6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| West | [View](plots/permission-west-front.png) | [View](plots/permission-west-back.png) | [View](plots/permission-west-inner1.png) | [View](plots/permission-west-inner2.png) | [View](plots/permission-west-inner3.png) | [View](plots/permission-west-inner4.png) | [View](plots/permission-west-inner5.png) | [View](plots/permission-west-inner6.png) |
| East | [View](plots/permission-east-front.png) | [View](plots/permission-east-back.png) | [View](plots/permission-east-inner1.png) | [View](plots/permission-east-inner2.png) | [View](plots/permission-east-inner3.png) | [View](plots/permission-east-inner4.png) | [View](plots/permission-east-inner5.png) | [View](plots/permission-east-inner6.png) |

## Remaining release work

Complete routing and return paths on both boards, pulldown returns and startup
review, protected outputs and thermal copper, analog/module distribution,
load/fault/startup qualification, accepted stack/plating, approved ESS package
inputs, exact BOM, interfaces, installed housing/cooling/harness fit, reviewed
manufacturing outputs and the prototype bring-up plan. The historical TBP35
inlet resistance screen does not model current copper or current sharing.
No fabrication release or order has been made.
