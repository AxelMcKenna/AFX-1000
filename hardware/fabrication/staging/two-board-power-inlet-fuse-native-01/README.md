# TBP35 — inlet fuse orderable-part correction

**Partial design; not released for fabrication.** Open the
[power/protection project](power_protection.kicad_pro). The signal board is
unchanged and still has 251 opens; this power board still has 2,372.

I_F1 now specifies **045106.3MRL, 6.3 A, 125 V**, replacing the unsupported
`0451006.MRL 6A 125V`. The schematic, embedded/library symbol values,
board value/MPN and circuit contract agree. The [manufacturer review](../../parts/inlet-fuse-01/README.md)
records the source, conditional loss estimate and remaining derating/fault
coordination work. This is a backup fuse, not the normal current regulator.

The [independent audit](inlet-fuse-review.json) proves exact equality of the
complete board tree after restoring only the fuse's two property values.
All 6,427 captured copper objects, 21 zones and 3,110 current native groups
are unchanged. Fifty-five KiCad-generated pad identifiers are mapped by
unique complete physical equivalence; no physical pad changes. The audit
also checks 226 CAD/support files and all 3,420 schematic pin-net entries.

[Native checks](review.json) report zero geometry/parity/ERC errors and the
same two isolated-reference warnings. The package remains within its previous
body/height allocation and nominal lands match the published dimensions.
Complete installed fit and assembly-process acceptance remain unfinished.

Because copper is exactly unchanged, the inspected TBP34 exports still show
this revision's copper: [front](../two-board-power-input-tvs-native-01/plots/front.png),
[back](../two-board-power-input-tvs-native-01/plots/back.png),
[inner layers](../two-board-power-input-tvs-native-01/plots/inner-contact-sheet.png).
Their [visual review](../two-board-power-input-tvs-native-01/plots/visual-review.json)
is historical evidence carried forward by the exact geometry comparison.

Input TVS and the complete fused DC-input net remain connected. AUX return
is still separate, G_NT1 is still isolated, and all prior ground-reference
coverage is preserved. Current capacity, voltage drop, thermal/transient and
fuse/adapter qualification remain open. Complete supply and return routing,
signal routing, ESS package inputs, accepted manufacturing stack/BOM/process,
whole-unit fit and prototype inspection/bring-up work are still required.
