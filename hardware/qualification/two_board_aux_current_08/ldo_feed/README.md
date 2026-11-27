# Local IN feed — isolated source09 candidate

Final `inputs-review-02/power_protection.kicad_pcb` SHA256 `f2b09b6ae0fbc04a1d0b1dc46cc7a663c62471fd06933dd381810f80f0b6d66f` connects the previously isolated U102 IN8/C907positive group to source-connected AUX_PREREG5 copper. Open count1943→1942; EN5 remains unrouted. Source is reference09, not the separate C13 repaired candidate. No accepted power selection changes.

Only new C907 shifts west1mm to(186.5,126.6). Four previously owned local-bypass tracks are replaced by seven tracks and two .6/.3mm through-vias. Signalvia(186.1,123.5), paired AGNDvia(185.2,123.5), distance.9mm, sit in the exact1mm slot between DC_IN endingY123 and MODULE_FEED beginningY124. Foreign fills are retained exactly; no MODULE_FEED neck reduction is introduced. Native DRC confirms no added clearance violation. New C907 receiving box translates unchanged and clears1940peers, including .77mm to U102's receiving box, under root's still-provisional assembly budgets.

Five main-ground polygons receive only explicit exact corner runs from the bounded14.33s selected-zone fill. Six-zone full native fill is rejected as a final board because it healed remote areas. `retain_local.py` restores source geometry everywhere except the enumerated antipad runs. Native chord corners can reach beyond a .506mm circle (the point186.018123,122.9995 is about.50715mm fromvia), so the explicitly reviewed enclosing bound is.508mm. This is a bound on copied native corner coordinates, not extraction quantization and not a .20mm clearance waiver. The .501/.506 radius attempts are retained as rejected scripts. No additional F.Cu plane cut was accepted.

First native review rejected two off-center via endpoints and one .1733mm F.Cu ground clearance. The correction centers both endpoints and routes the capacitor-positive lead around all existing F.Cu ground copper. Final no-refill DRC has zero schematic-parity defects and only the same four unwaived DSE clearances. Native comparison proves exactly one declared source-group merge, every other original pad group and identity preserved.107 original main-ground contacts and2206 original surface-track reference areas are unchanged. Actual new signal track exceptions are confined to the copied via antipad; the paired return via is fully covered by connected main-ground fill on both adjacent reference layers. Contact keepouts remain clear.

The direct capacitor-ground lead is now4.1181mm, and the positive lead1.6464mm. This longer bypass loop is a conditional candidate, not proven short-loop/transient acceptance. Current, effective capacitance, actual copper thickness/resistance, regulator thermal performance, startup and hold-up qualification remain open. Geometry/DRC and preserved contacts do not establish those electrical bounds. Source09's C13/C16 conflict and the L900/N_U22 tail conflict are separate receiving gates; C13 repair exists in cb63b977 and is not silently combined here.

Verification:
```
python3 -m hardware.qualification.two_board_aux_current_08.ldo_feed.verify
python3 -m hardware.qualification.two_board_aux_current_08.ldo_feed.check_local
python3 -m hardware.qualification.two_board_aux_current_08.ldo_feed.verify_transition
python3 -m unittest tests.tooling.test_aux_ldo_feed
```
Four reference/mutation tests pass. Self-review caught the via-centering and F.Cu clearance defects and retained rejected evidence before correction. Immutable inputs, host/native input hashes, process signals/timeouts, source/candidate identities and final native evidence are retained; the47MB native evidence JSON is losslessly gzipped for handoff. No fabrication-rule relaxation or PCB promotion occurs.
