# Isolated AUX buck routing checkpoint

`native-04/power_protection.kicad_pcb` is a **separate, incomplete PCB candidate**, based on frozen TBP73. It adds all 18 proposed components and routes the new buck's local connections with **29 B.Cu tracks and three 0.6/0.3 mm ground vias**. It does not retarget any original pad or perform the existing supply cutover. The held-supply cell, reset supervisors and long held-rail distribution remain unrouted. Do not replace the accepted board with this file.

## What is implemented and verified

All sixteen planned local connections are natively connected. The input-capacitor/VIN route is 1.675 mm; SW-to-inductor is 1.965 mm. The IC PGND-to-ground-via route is 1.379 mm, exposed-pad route 2.0 mm, input-capacitor return 1.188 mm and output-capacitor return 1.9 mm. Feedback resistors were repositioned within the isolated candidate: P_R901 to (196.7,147.1), mathematical back-side rotation 90°, and P_R900 to (199.6,147.7), rotation 0°. This shortened the lower-divider-to-AGND route from 12.6 mm to **2.236 mm**. Exact native angles and poses are in `placement.json`; the earlier placement checkpoint remains unchanged.

The three new ground vias are at (191.5,147.5), (192.4,140.9), and (199.3,153.075). They are outside pads; the planner checks every copper layer and foreign filled zones. All three have actual native connectivity to the existing main-ground group. Every new surface route's full width is covered by the existing anchored In6 main-ground fill. No new zone, plane extension or refill is used in this checkpoint.

The native before/after audit preserves **all 2,674 original connectivity groups**, all original pad/track states, and all **47 zone outlines and filled polygons**, including complete raw polygon geometry. All original explicit pad identities are checked independently. These checks preserve the quiet networks' existing contacts and connectivity as well. A separate geometric exclusion checks 111 retained AGND objects authored by both quiet-network passes (pads, tracks and vias) plus all seven networks' zone outlines, and finds no new contacts. They do not substitute for a separate quiet-network contact audit if a future In6 extension or wider distribution is authored.

The ordinary ground via near the exposed pad is not a verified thermal design. TI's package soldering, thermal spreading, assembly process and actual regulator load remain qualification requirements. The VOS sense route is 10.114 mm and goes around the switching geometry; its EMI/ripple behavior has not been qualified. Native electrical connectivity alone does not establish regulator performance or accept the long sense path.

## Native findings retained

Pinned Linux KiCad 10.0.7 reports **four errors and zero warnings**. All four errors are the known TPS3703 DSE copper clearance conflicts: pads 1–2 and 2–3 on each of E_U900 and P_U902 have 0.15 mm clearance against the unchanged 0.20 mm rule. No rule exception, severity reduction or ignored check was added.

New component references, values and polarity artwork use the assembly layer because this dense placement cannot carry the default library silkscreen positions. Explicit `AUX_ROUTE` library variants retain the original copper/package geometry and carry these presentation changes, so native library comparisons remain enabled and pass. Source and variant hashes are retained in the native review. The native candidate has **1,964 uncapped opens**, versus 1,936 in the accepted baseline: the additional components are not yet integrated into the existing supplies. The CLI JSON's 499 unconnected records are capped; they are not the native open count. Schematic/PCB parity has not been claimed or accepted.

`native-04/local-native-copper.png` is a reviewed rendering of actual native B.Cu objects over the actual In6 fill, not the planner's proposed centerlines. `local-native-geometry.json` binds it to the candidate PCB hash. Earlier native-02/native-03 files are rejected intermediate outputs and are not part of this checkpoint.

## Anonymous source pad identities

The original PCB has **55 pads without UUIDs**: 49 electrical pads explain the capture/native connectivity ID differences, and six unnetted/unnumbered pads belong to G_U1. They receive different generated UUIDs on separate KiCad loads. `identity_native.py` therefore checks all **3,666 explicit source pad UUIDs and physical identities exactly**, and exports full physical identities for every anonymous-source pad. The identity includes reference, pin, absolute pad and footprint pose/side, shape, size, drill/attribute, offset, layer set, round/chamfer geometry, net and native copper polygons on every layer.

`anonymous-pad-mapping.json` records every one of the 55 capture-to-candidate mappings, both PCB hashes and the capture/native-evidence hashes. Matching is bijective and rejects duplicate physical identities; only source pads lacking UUIDs are remapped. Full physical identity must remain identical. Tests deliberately move, resize and re-net an anonymous pad and insert a duplicate identity; all are rejected. The 49 electrical mappings are used only to compare the separately captured baseline groups with the native before/after audit. This is not permission to ignore physical changes or explicit UUID mismatches.

## Remaining supply and return work

The first local buck routes are complete as connectivity, but no upstream VIN connection or downstream P_U102 cutover has been authored. P_U102 IN/EN and P_C102 belong to an existing 24-object VIN group; reassignment requires an explicit branch cut. E_U31.6, E_U29.8, E_U31.8, E_C74.1 and E_C76.1 share a 188-object main-AUX group, so blindly changing pad nets would short the supplies.

The physically local U1/C29 and U2/C36 positive branches are isolated three-object groups with 3.986 mm and 7.088 mm existing traces. C29/C36 are 100 nF, 16 V, X7R 0805 in the current BOM, with no exact MPN; **both ground pads are disconnected**. Their complete isolated branches are candidates for held-supply reassignment, with a corresponding explicit schematic revision, but proper return routing/loop proximity and capacitor procurement still need proof. The current C1 assignment would instead cut a branch feeding E_U11. U3/C9 has a 2.887 mm supply branch and anchored capacitor ground. U4/C13 has no positive connection and a 13.172 mm straight span, so it likely needs a local placement revision.

The held LDO location is outside the present In6 fill. A potential In6 extension beneath the held cell is not authored here: it needs filled-contact, quiet-pad/track/through-hole exclusion, retained-reference and exact native group-delta checks. The approximately 50 mm 5 V feed, 58 mm sense connection and up to 113 mm held supply spans remain unrouted. Wider copper or a plane-based distribution with verified return resistance is still required to meet the **conditional** 20 mV allocation. The actual-current, capacitance, reset loading, discharge, startup and thermal limits remain unresolved as documented in `held_rail`.

## Checks

Run `routed.verify <root-integration-worktree>` to check native artifacts, all source hashes, complete original fill geometry, native connection groups, exact retained DRC errors, and anchored returns. Eight regression tests cover unrelated-group merging, lost via contact and anonymous-identity failures. Existing package/placement tests remain separate. All Linux operations used the pinned image and read-only baseline mounts; no native Mac CAD was launched. This is a self-reviewed isolated layout checkpoint, not an independent review, fabrication release or completed housing fit.
