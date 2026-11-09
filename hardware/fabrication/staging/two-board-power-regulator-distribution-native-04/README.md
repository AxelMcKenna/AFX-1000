# TBP36 — main regulator supply and return distribution

**Partial routing; not ready for fabrication.** Open the
[power/protection project](power_protection.kicad_pro). Both main regulator
input cells now connect to the protected bulk supply, and U23's local return
joins the main return. This closes three connections: **2,369 power opens
remain**. The signal board remains at 251 opens.

## Layout change

One In2 supply zone connects the U101/C103 source group to U20 and U23 through
their existing input vias and local In3 planes. It passes around the retained
PGTH sense route. Two In1 ground bridges provide the adjacent return path:
one joins the existing U20/source ground fields, and the longer bridge joins
the source and U23 fields. The ground bridges have explicit priority 1 where
they overlap existing same-net zones.

| Added zone | Layer | Filled area | Filled pieces |
| --- | --- | --- | --- |
| Regulator feed | In2 | 705.498 mm² | 3 |
| Digital return bridge | In1 | 16.914 mm² | 1 |
| Analog return bridge | In1 | 785.536 mm² | 1 |

All three supply pieces connect through actual existing vias and local In3
copper; this is not one uninterrupted In2 sheet. No components move and no
tracks, vias, values, packages or schematic pin assignments change. The
045106.3MRL inlet-fuse correction is retained. AUX return, its local copper,
G_NT1 isolation and the regulators' quiet-return geometry are preserved.
P_J22.2 remains unjoined, with an explicit reserve in the new ground zone.

## Verification

[Native checks](review.json) report zero geometry, schematic-parity or ERC
errors, with the same two isolated-reference warnings. All checks remain
enabled. There are 1,086 electrical components, 1,101 footprints, 2,444 tracks,
262 vias and 24 filled zones.

The [independent audit](regulator-distribution-review.json) verifies the whole
non-zone PCB tree, all 6,427 captured physical objects, all 3,110 previous
connection groups and all 3,420 schematic pin-net entries. Only the two
declared supply-group joins and one return-group join occur. Seventeen old
fills remain exact; four refill, with every old zone outline unchanged.
The In2 inlet fill has a small native refill delta, so the earlier TBP35
resistance calculation is historical evidence rather than an exact calculation
of this complete new distribution network.

All 228 previously complete full-width adjacent-ground track projections
remain covered by their corresponding native ground group. The
[new-feed reference review](regulator-reference-review.json) finds 99.9936%
coverage after excluding supply-contact antipad margins. The remaining
0.043961 mm² comprises eight small regions at supply-via banks and the
isolated header reserve. Full-area coverage, impedance, noise and thermal
qualification are not claimed. Minimum new-zone foreign-copper gaps are
0.19949 mm or greater in the approximately 0.001 mm-error native capture;
native DRC is clean.

The [originally rejected-net review](rejected-source-net-status.json) still
finds eight of those 52 source nets complete and 44 incomplete. It does not
count partial routing as a completed circuit.

## Actual copper views

[Front](plots/front.png) · [Back](plots/back.png) ·
[Six inner layers](plots/inner-contact-sheet.png) · [Visual review](plots/visual-review.json)

| Detail | Ground In1 | Supply In2 | Retained local inputs In3 |
| --- | --- | --- | --- |
| U20 and source | [View](plots/distribution-left-inner1.png) | [View](plots/distribution-left-inner2.png) | [View](plots/distribution-left-inner3.png) |
| U23 | [View](plots/distribution-right-inner1.png) | [View](plots/distribution-right-inner2.png) | [View](plots/distribution-right-inner3.png) |

## Remaining work

Qualify the new branches' actual current sharing, voltage drop, startup and
thermal behavior using the accepted stack and integrated loads. Complete
regulator output distribution, force/quiet returns, remaining module input
branches and signal/power routing. Effective capacitance, control timing,
surge/fuse coordination, exact BOM/process, ESS package inputs, manufacturing
outputs, whole-unit installed fit and prototype inspection/bring-up remain
unfinished. No fabrication order or release is authorized by these checks.
