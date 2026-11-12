# AUX package census and conditional operating window

All 81 AUX-powered IC packages, across 29 orderable families, are now assigned manufacturer table-current rows and explicit conditions. The four Si8751 rows contribute 38 mA and the other 77 package rows contribute 0.727 mA. Adding the existing independently owned resistor/output-port terms gives **58.302212 mA** as a mixed-condition sensitivity. It is not a whole-board current bound: several tables specify other supply voltages, rail-to-rail inputs, a particular output state, or a different load. Transition current, actual gate loading, clamp/interface currents and fault states are still unresolved.

`facts.json` binds the original PDFs and extracted text. The LTC2910 manufacturer PDF was inspected online at its original ADI URL, pages 2–3, giving 100 µA maximum over 2.3–6 V; local retrieval failed (HTTP/2 termination, then HTTP/1.1 timeout), so its web table review is explicit rather than a fictitious local file. Its reference output load is already owned in the parent port ledger. The full text sources retain their original formatting.

Corrections applied in the census:

- TLV1824 has four channels and TLV1822 two: 18 comparator channels across five packages. OPA2333 has two channels: four amplifier channels across two packages.
- SN74AUP2G08 uses the electrical-table 1.7 µA maximum, rather than the front-page 0.9 µA statement.
- N_U16 draws AUX from translator rail A; N_U27 from rail B. Each uses its own 3 µA table row. The combined 4 µA two-rail figure is not assigned wholly to AUX.
- A common −40 to 85°C screen is the intersection used here; this does not silently claim all selected AUP devices are characterized to 125°C.

## Regulator and supervisor

The actual TBP71 divider is P_R108 = 11.7 kΩ, P_R130 = 49.9 Ω, P_R109 = 10 kΩ. With the TPS7A16 nominal 1.193 V reference, it targets **2.594763 V**, despite the `V2V5` net label. Using ±2% overall regulator accuracy, ±0.1 µA feedback-current sensitivity, and stated resistor initial tolerance plus TCR over a 100°C deviation yields a conditional **2.534165–2.655699 V** output interval. Aging, assembly and receiving variation are not included. The overall accuracy row already covers specified load/line conditions; adding its separate regulation rows again would double-count them.

Five TLV182x packages require at least **2.4 V**: E_U9, E_U10, E_U18, N_U14, N_U15. The historical 2.3 V lower screen therefore cannot be used for their functional qualification. The conditional regulator interval leaves 134.165 mV for distribution and transient drop before reaching 2.4 V; that is an available allocation, not a measured drop or proof of operation. The regulator accuracy requires the stated input/load conditions; nominal output plus 0.5 V is 3.094763 V. TPS7A16 PG by itself may release below 2.4 V and is not proof of comparator validity.

The actual E_U19 TPS389001 AUX supervisor has a different divider: E_R137 = 11.1 kΩ, E_R138 = 39.2 Ω, E_R139 = 10 kΩ. Its nominal falling threshold is **2.431008 V**. With only stated initial 0.1% resistor tolerances, 1% threshold accuracy and a signed ±100 nA sense-current sensitivity, the low corner is **2.403049 V**, leaving only **3.049 mV** before the comparators' minimum. The sense-current table point is 5 V, not the actual 1.15 V threshold, so even this is conditional. TCR, aging, local ground/drop differences and shutdown delay are not allocated by that number.

`threshold_window.py` provides an exact *proposed* design window. Under explicit requirements of ±0.3% total resistor error, ±150 nA sense current, 20 mV total shutdown drop/slew allowance and 15 mV startup allowance, the top resistance must lie between approximately **11.33885 kΩ and 11.47385 kΩ** with a 10 kΩ bottom. Existing 11.1392 kΩ is outside. A candidate E_R137 = 11.4 kΩ and E_R138 = 0 Ω link centers the window. No board/BOM/source schematic was changed: the allocations and entire downstream timing must be substantiated before accepting this correction. See `threshold-window.json` for exact margins and every acceptance requirement.

## Reproduction and review

Run from the repository root:

```
python3 hardware/qualification/two_board_aux_current_08/package_currents/analyze.py
python3 -m hardware.qualification.two_board_aux_current_08.package_currents.threshold_window
python3 -m unittest hardware.qualification.two_board_aux_current_08.package_currents.test_analysis
```

Nine checks pass: complete native package/rail ownership, missing/duplicate package rejection, channel-count underestimation, unproven-bound rejection, independent regulator-corner enumeration, supervisor margin semantics, candidate allocation feasibility, and an infeasible larger-drop case. Self-review corrected an initial assumption that both translators used AUX on rail B, corrected the comparator table's default supply to 12 V, and derives comparator references from the census rather than hand-entering them. These calculations advance the source/current/voltage review but do not establish a run/startup/fault bound or release fabrication.
