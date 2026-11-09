# AUX feedback parts and TBP51 working candidate

The three AUX regulator feedback positions now have exact manufacturer part
numbers in a separate [KiCad candidate](../../staging/two-board-power-aux-feedback-native-01/power_protection.kicad_pro).
Their nominal resistances and circuit connections are unchanged. The selected
public checkpoint remains TBP50; this candidate is not a fabrication release.

| Reference | Manufacturer part number | Nominal resistance | Initial tolerance / TCR |
| --- | --- | --- | --- |
| P_R108 | Vishay TNPW080511K7BEEA | 11.7 kΩ | 0.1% / 25 ppm/K |
| P_R109 | Vishay TNPW080510K0BYEA | 10 kΩ | 0.1% / 10 ppm/K |
| P_R130 | Stackpole RNCF0805TKY49R9 | 49.9 Ω | 0.01% / 5 ppm/K |

[BOM CSV](bom.csv) includes the exact catalog and datasheet links.
[Selection and calculation](selection.json) binds the source design and files.
Catalog listings establish identifiable parts, not reserved stock, price or
delivery. Recheck sourcing before purchase; the 11.7 kΩ listing is non-stocked.
P_R108's former 10 ppm label is changed to match the selected 25 ppm part.

## Electrical calculation

Nominal output remains **2.594763 V**. With complete installed limits of ±1%
for P_R108/P_R109 and ±3% for the small P_R130 trim, the conditional steady-state
source interval is **2.514387–2.676853 V**. It leaves 214.387 mV for supply and
return distribution loss before the monitor's 2.3 V minimum, and 23.147 mV below
the existing 2.7 V upper screening boundary. The larger trim allocation changes
the former all-1% limits by less than 0.123 mV.

The calculation includes the regulator's ±2% overall accuracy and signed
±0.1 µA feedback current, with positive current flowing out of FB. Required
regulator load, input headroom and temperature conditions still apply. Initial
tolerances alone give 2.538955–2.650691 V. There are 64 corner cases across the
two scenarios, with nodal and independent decimal checks. Maximum resistor
power in the installed-limit screen is 0.179 mW, 0.150 mW and 0.000778 mW for
P_R108, P_R109 and P_R130 respectively.

The installed limits are design requirements, **not qualified lifetime bounds**.
For the two Vishay parts, a compound screen of initial error, a 105 K temperature
excursion and the listed separate assembly/environment/endurance tests consumes
0.8361% and 0.6778% respectively. The report retains each term. Combining
separate test limits does not establish combined-stress behavior, an 8,000-hour
product lifetime, or the actual installed temperature. Film temperature, product
service conditions and process qualification remain to be established.

## Lands and verification

P_R108 and P_R109 use a new local library footprint with 0.90 × 1.45 mm
rectangular pads, 1.00 mm inner gap and 2.80 mm overall span. These follow the
IPC-based reflow row in [Vishay 28950](https://www.vishay.com/doc?28950).
The two affected local ground fills were regenerated. All other 45 fills were
verified unchanged. No track, via, placement or zone outline was authored.

P_R130 retains its generic 0805 lands. Its exact part is catalogued, but the
current full Stackpole datasheet and land/process review remain open. Direct
manufacturer downloads failed; the downloaded distributor copy is from 2015
and is retained as historical research only. It is not used to qualify current
drift limits. Current indexed manufacturer material shows changed performance
limits, so the old precision-specific test figures must not be carried forward.

The [native report](../../staging/two-board-power-aux-feedback-native-01/review.json)
records zero geometry or parity findings, two retained ERC warnings and 2,172
opens. The [delta review](../../staging/two-board-power-aux-feedback-native-01/aux-feedback-review.json)
checks exact circuit preservation, all native connectivity groups, changed-pad
scope, local fill changes and retained reference coverage. This is evidence for
the narrow BOM/land revision; it does not qualify the entire AUX supply or unit.

Source PDFs and reviewed page images are retained in `sources/` and `review/`.
Vishay 28758 revision 10-Apr-2026 pages 2–4 and 12–14, and 28950 revision
12-Jul-2022 page 1, were visually inspected. See [review record](primary-review.json).

Next: finish the Stackpole review, establish installed resistor bounds, then
continue AUX package/pin-current, startup, voltage-drop and thermal work.
The broader routing, ESS footprint, housing and manufacturing blockers remain.
