# TBP42 startup logic ground references

**Development checkpoint; not ready for fabrication.** The power board retains
**2,294 open connections**. Native geometry, schematic parity and ERC errors
are zero, with the same two isolated-reference ERC warnings. Signal remains
at 251 opens with its approved ESS codec footprint missing.

All **33 current non-ground logic route sections** now have complete adjacent
ground projection under the recorded via-antipad exclusions. TBP41 had 2/32;
splitting PG1 at a new transition adds one screened section. This is geometric
reference coverage, not proof of noise, timing, current or thermal performance.

Three main-ground zones are added on In1/In4, and existing In5/In6 main-ground
outlines extend around the logic and AUX branches. Each new filled component
connects to the existing main-return group. An unconnected proposed region was
discarded before authoring. PG1 transitions below the supply field; FOLLOW1
uses the existing enable via and runs around the quiet fields. Neither reroute
cuts a quiet return. No footprints, component values or schematic nets change.

18 tracks and two vias replace eight tracks and one via. Current totals are
2,693 tracks, 339 vias, 39 zones, 6,753 captured physical objects and 3,032 native
connection groups. All 1,101 footprints, 1,086 electrical parts and 3,420
schematic pin entries remain. **No additional open connections close in this
pass; all prior connections are preserved.**

The independent [geometry and connection audit](logic-reference-review.json)
verifies every declared copper change, exact undeclared board content, unchanged
native connection partitions, all four star-only quiet returns, 305 retained
complete ground-reference cases, 22 own-field ILM/DVDT screens and all 20 source
plane contacts. Thirty existing zone fills remain exact; six original fields
refill. No clearance rule is waived.

The first reference candidate unintentionally trimmed the digital supply field.
Controlled native refills isolated the effect to the added ground zones. The
corrected candidate gives the existing In4 supply field priority 2 ahead of the
priority-1 references. Its filled copper exactly matches a separately refilled
control containing only the declared track/via replacements on the original
board, with every original zone definition retained. This removes the added
ground field's unintended trim. The control and candidate both reproduce a
small native remeshing change outside the via neighborhoods; it is recorded in
the audit rather than hidden by a wider tolerance. See the
[refill control](../two-board-logic-reference-refill-diagnostic-01/reroutes_only.json).

The In4 source remains one 836.210249 mm² field. Its uncovered In5 projection
remains 0.355273 mm². All 33 fast-overvoltage sections retain reference coverage.
Earlier support sections remain 24/28 complete; retained TBP40 startup sections
improve from 6/15 to 7/15. Those remaining references still need work. See the
[retained route review](retained-logic-reference-review.json).

Next work includes U29 ALL_RAILS_ALLOW, U30/U34/U41 supplies and bypass, remaining
gate/receiver paths and PG pull-up AUX ends. Protected outputs, thermal copper,
analog/module supply and return paths, remaining signal routing, approved ESS
inputs, accepted stack/plating, exact BOM, complete installed housing fit,
reviewed manufacturing outputs and a prototype bring-up plan remain required.

## Native views

[Front](plots/front.png) · [Bottom](plots/back.png) · [Inner overview](plots/inner-contact-sheet.png)

[Logic front](plots/logic-front.png) · [Logic bottom](plots/logic-back.png) ·
[In1](plots/logic-inner1.png) · [In2](plots/logic-inner2.png) ·
[In3](plots/logic-inner3.png) · [In4](plots/logic-inner4.png) ·
[In5](plots/logic-inner5.png) · [In6](plots/logic-inner6.png)

All eleven views were directly inspected. The detail viewport covers both the
logic cells and the long AUX/AUX_VALID routes. Native SVGs and source-bound
render records accompany the PNGs. [Native results](review.json) and
[construction record](logic-reference-routing.json) identify the exact board.
