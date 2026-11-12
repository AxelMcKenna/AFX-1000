# AUX ledger self-review

This is a self-review, not an independent electrical review.

- Corrected the initial assumption that 22 logic and 12 NF pulldowns were disjoint. Native branch membership shows the 12 are included in the 22. The verifier rejects an added NF branch even if it has a different row ID and the arithmetic is adjusted.
- Excluded E_R94 from logic pulldowns because its reference-output current is already included in the reference model. Preserved separate source-port ownership for shared resistor networks.
- Checked historical pin maps, resistor nominal values and all 45 direct AUX roots against TBP71. A leading root slash is normalized only after checking unique names. No electrical topology discrepancy was waived.
- Preserved metadata changes and conditional resistor/voltage assumptions. The ledger is not marked as a complete current, startup, thermal or fabrication acceptance.
- Checked current primary regulator/isolator tables. The Si8751 load/IN conditions and TPS7A16 current-limit scope do not support promoting the subtotal to an installed bound.
- Tests intentionally exercise erroneous membership and unsupported acceptance, not just successful regeneration.

Remaining: package/current-state models, actual component receiving bounds, external loads, full source/drop/ramp and installed thermal verification. These remain task work, not reasons to declare this design complete.
