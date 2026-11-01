# Independent U11.5 receiving escape screen — proposal only

Source: immutable `schmitt-u37-backbone-clear-work`, PCB SHA b922460f8129094b9760e5eb229602b83013f82248d56c82d9b4f85200a1d967. No repository source was edited. All work is in this temporary folder.

Candidate0 adds one actual0.6mm-land/0.3mm-drill filled/capped receiving barrel on N12_OV_OK_SCHMITT at local(7.300,13.975), with the actual0.2mm F path in `candidate0-receipt.json`. Its centreline is about1.676mm. It preserves every existing1447via, every physical footprint/port/pad geometry and every force/quiet/GND track. The suppliedRouter geometry and exact buffered segment checks permit this escape after explicitly removing30 ordinary-control fragments:18P12_OV_OK_SCHMITT and12N19_OV_OK. Every removed full source object/UUID is retained. No rule was reduced.

This is a **joint restoration proposal**, not a closed three-net repair: P12buffered andN19raw must be deliberately rejoined. The new receiving barrel also needs its onward N12connection. The existing obsolete target(10,14.5) is physically invalid: its centre is only0.1mm from the realP19_OV_OK barrel(10,14.6); two0.6mm lands plus0.2mm clearance need0.8mm centre separation. The newsite's nearest oldbarrel isP12_OV_OK_SCHMITT(6.75,14.6), distance0.83254mm, giving only0.03254mm nominal copper-clearance margin over0.2mm. This is nominal native geometry, not drill/etch/registration or manufacturing acceptance.

Actual KiCad10.0.7 all-track-errors/schematic-parity/severity-all/refill/save native checks were run independently on an untouched source clone and candidate clone:

- Baseline:0hard,152warnings,41opens,0parity.
- Candidate:0hard,156warnings,45opens,0parity.
- Both inherit the same five stock ignored checks; this is NOT an all-ignored-cleared or fully-routed pass. Full raw JSONs are retained.

`comparison.json` compares actual freshly saved fills from both native runs. Only AGND changes at the reported numerical resolution: In1withdrawn2.715230mm²/added0.000091565mm²; In4withdrawn1.005491mm²/added~0.000000030mm². It is not a no-pour-loss solution. The comparison uses actual native filled polygons, converting128 fractured/keyhole polygons per board with Shapelymake_valid; it is a geometric diagnostic, not an electrical resistance bound. No force/current/quiet-ground/thermal/noise result is inherited.

Native saving generates missing nested-pad and four mounting-footprint UUIDs in this old source. Raw UUID differences are retained in the report, and all273completefootprint geometries/properties compare exactly after removing only UUID fields. All1447originalvia objects and all surviving32158originaltrack objects are otherwise exact;30source tracks removed/10newFsegments added/one newvia added.

For a merge, apply ONLY the30explicit removals plus10new segments/onevia to the owner's new coherent source after verifying the original local objects still match. Do not overwrite a whole board with this snapshot. Rejoin both displaced control nets and perform fresh full native/filled return/force extraction. All physical, routing-complete and qualification flags remain false.
