# TBP43 — U30/U34/U41 startup routing

Development checkpoint, **not ready for fabrication**. The power/protection
board has **2,267 native open connections**, down from 2,294 at TBP42.
The signal board remains at 251 opens with its approved ESS footprint missing.

U30, U34 and U41 move with their existing 100 nF bypass capacitors C75, C77
and C84. The 23 targeted interconnects include restored inputs, master enable,
Schmitt receivers, analog/digital enables, PG pull-up signal ends and AUX
supplies. Six main-ground and three local bypass joins complete **27 net new
connections** after accounting for restored pre-existing connections.
ALL_RAILS_ALLOW, pull-up AUX ends, remaining returns and the wider startup
chain remain unfinished. No part value, package or schematic pin net changes.

The revision adds 178 tracks and 49 through vias, retires 14 obsolete tracks
and two obsolete vias, and extends four existing main-ground outlines.
The result has 2,857 tracks, 386 vias, 39 zones and 3,005 native connection
groups. All 1,101 footprints, 1,086 electrical components and 3,420 schematic
pin entries remain; six footprints and 30 pad positions change.

## Verification

- Native geometry, schematic parity and ERC errors: **zero**. Two existing
  isolated-reference ERC warnings remain; 2,267 unrouted connections remain.
- [Independent audit](startup-completion-review.json): all 27 declared group
  merges, every other existing connection, all six moves and declared copper
  changes verified against the native capture.
- All **70 new non-ground route sections** have adjacent ground projection,
  excluding only their own net's recorded via antipads. This checks copper
  coverage, not impedance, return inductance, delay or noise performance.
- **486 retained complete reference cases**, 22 own-quiet reference sections,
  four star-only eFuse returns and all 33 fast-OV sections are preserved.
- Source In4 copper is unchanged, with all 20 contacts and one filled region.
  Thirty previous zone fills are unchanged; nine refill. Ground components
  have verified electrical ownership, including the overlapping In5 main fields.
- [Retained-reference review](retained-startup-completion-reference-review.json):
  support coverage remains 24/28; retained TBP40 startup coverage remains 7/15.
  In5 projection beneath the source retains approximately 0.355273 mm² uncovered.
- Hole spacing and drill-to-SMD checks pass. Placement/courtyard/body/tail checks
  remain provisional assembly screens, not a complete installed housing fit.
- [Visual review](plots/visual-review.json): eleven current views directly inspected.

Native candidate 03 exposed an obsolete PG2 stub, removed in candidate 04.
Candidate 05 closed the final FOLLOW3 interconnect. Candidate 06 reroutes five
inner paths to avoid reference gaps at existing In1 signals, a bottom fanout
projection and via exits. Earlier candidate findings were corrected, not waived.
The [construction plan](../two-board-startup-completion-plan-06/README.md)
retains the exact inputs and search history.

## Current copper

[Front](plots/front.png) · [Back](plots/back.png) ·
[Six inner layers](plots/inner-contact-sheet.png)

[Startup front](plots/startup-front.png) · [Startup back](plots/startup-back.png) ·
[In1](plots/startup-inner1.png) · [In2](plots/startup-inner2.png) ·
[In3](plots/startup-inner3.png) · [In4](plots/startup-inner4.png) ·
[In5](plots/startup-inner5.png) · [In6](plots/startup-inner6.png)

## Remaining release work

Complete routing and return paths on both boards, startup/control distribution,
protected outputs and thermal copper, analog and module supplies, load/fault/
startup qualification, accepted fabrication stack and plating, ESS package
inputs, exact BOM, interfaces, installed housing/cooling/harness fit, reviewed
manufacturing outputs and the prototype bring-up plan. The historical TBP35
inlet resistance screen does not model current copper or current sharing.
No order or fabrication release has been made.
