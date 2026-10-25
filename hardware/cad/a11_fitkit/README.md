# A11 compact mechanical fit trial

This kit tests the actual A11 button, holder, guide, panel, knob and selector interfaces before committing to the 334 × 157 × 38 mm housing. It contains **30 distinct printed designs / 38 copies**, with every individual part smaller than 40 mm in XY. It is a physical trial kit, not a measured fit approval or a complete housing.

The five stations use `quantize`, `auto`, `pad_0`, `pad_1` and `scene_2`. Together they cover all five holder mounting patterns, the narrow rectangular path, the USB-clearance mounting pattern and the curved Scene FX cap. Each station has its own key, switch holder, cropped panel and cropped guide. Panel/guide pieces are cut directly from the A11 model in the button's local frame: neighbouring apertures and thin webs are deliberately retained. The outer crop edges are fixture edges, not proposed changes to the full housing. Eight retaining clips provide five working clips and three spares.

The four actual A11 knob variants are included (Ø16 × 13, Ø17 × 15, Ø29 × 18 and Ø32 × 18). A shared pot panel/guide trial and a shared selector panel/guide trial use the actual A11 apertures; two selector caps let the two selected switch types be tried. No generic shaft coupon is duplicated. Pot-body support, actual shaft/bushing hardware, springs and silicone contacts remain purchased-part selections.

## Build and print

From the repository root, with the A11 Python CAD requirements installed:

```sh
python3 -m hardware.cad.a11_fitkit.build --openscad /path/to/openscad
python3 -m unittest discover -s tests/tooling -p test_a11_fitkit.py -v
```

The build writes `build/artifacts/cad/a11-fitkit/RMX-A11-compact-fit-kit.zip`, individual STL files, `parts.csv`, native logs and checks. The ZIP includes `CAD/a11_fitkit/fixture.scad` and its frozen A11 SCAD dependencies at the matching relative paths, so it can be opened in OpenSCAD. The Python rebuild command requires the repository. Print only the inventory under `STL/`; any zero-depth contact meshes under `Native-Checks/` are diagnostic evidence, not printable parts. `hardware/validation/mechanical-fit/verification.json` fingerprints the fit-kit and A11 sources and records closed/connected positive-volume meshes and native motion/seating checks. A changed source invalidates the record. The existing A08–A11 sources and certificates are not edited or replaced.

Use **100% scale** and the quantities in `parts.csv`. STL Z=0 is the intended print face. Keep each station's panel, guide, holder and key together. The small envelope does not prescribe a material, machine, nozzle or print compensation. Preserve the 1.4 mm guide, 1 mm clips and narrow retained webs; inspect them in the slicer before printing. A mechanically tough process is needed for the clips and holder lips. Printed feel, strength, creep, surface finish and dimensional compensation have not been established.

## Assembly trial

1. Record machine, material/lot, layer/process settings, scale, orientation and any post-processing. Measure dimensions before filing, drilling, tapping or changing scale. Use the blank `MEASUREMENTS.csv`; the build never populates measurements or pass results.
2. Inspect one rectangular and one sector station first. Check the retained panel/guide apertures and screw holes against the supplied source geometry. If a crop leaves a fragile web, record that process failure; do not silently trim it away.
3. Fit each selected tactile switch to its holder. The A11 model uses a 6.4 mm case pocket and four Ø1.2 lead holes on a 6.5 × 4.5 mm pattern. These are existing model dimensions, not verification of purchased parts. The plastic holder is insulating; connect switch leads separately, not by soldering to printed plastic.
4. Assemble the panel at Z=0..2 mm, guide immediately below it at Z=-1.4..0 mm, and holder on the guide's underside. Insert the silicone contact, spring, key and retaining clip according to A11's assembly. Use two M2 holder screws per station; the nominal A11 choice is M2 × 10 into Ø1.6 pilots. Check actual screw tips, retention and clearances before tightening. Do not replace the soft contact with a rigid plunger.
5. Measure rest height, free movement, contact closure and full stop on **all five** stations. The nominal cap-to-panel gap and rigid travel are 1.2 mm. The cap should stop on the panel; the switch must close before that stop and open reliably at rest. The native sweep excludes the intended stop face only; it does not simulate compliant force or switch feel.
6. Cycle each station 100 times as an engineering trial. Record sticking, scraping, rotation, clip migration, cracks, spring buckling and failures to return. This trial is not a fatigue-life qualification. Record a force-versus-travel curve if instruments are available; total press force and subjective feel still need an agreed product target.
7. With the real pot supported by a suitable temporary insulating fixture, check all four knobs. Record shaft diameter/flat/projection, bore engagement, nut or bushing clearance where applicable, and pointer alignment. The model's bore is Ø6.2, blind engagement is at most 10 mm, and the modeled knob underside sits 2.8 mm above the panel. Those allocations require the actual selected pot. Do not force a fit, cut a shaft or treat a printed gauge as a calibrated shaft.
8. Try both selected slider switches with the selector station. Check real actuator engagement and every physical detent, including the centre Release position. The model has a 1.7 mm square cap socket; no universal travel or fit guarantee is implied.
9. Record any proposed dimensional change in the measurement sheet and revise a new prototype before printing the complete housing. Any changed mating surface needs fresh native checks and another physical trial. Reject binding, unreliable switch closure/return, damaged clips or screw interference before scaling up.

The worksheet's ±0.10 mm thickness and ±0.15 mm travel bands are **project trial criteria**, not manufacturer tolerances or evidence of a qualified printing process. A passed dimension alone does not override failed operation. All measurement/results cells start unperformed; acceptance requires the real selected parts and an identified reviewer.

## What this does not close

The kit cannot validate full chassis warping, printer capacity for the full enclosure, the 0.30/0.35 mm allocated E25/main-supply floor gaps, screw-tip/lead trimming, complete wiring, optical performance, return/contact force, lever motion/retention, vents or electronics operation. Full-size assembly and actual component heights remain required. E25 routing, the revised 5 V source/distribution candidate and the complete device remain unqualified. No parts were ordered and no physical printing or measurements were performed to produce this kit.
