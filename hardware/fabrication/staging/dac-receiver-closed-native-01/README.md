# E08 receiver layout integration candidate

This is the first routed physical candidate for the existing 60-part E08
receiver circuit. It closes the receiver-only layout gap. It does **not**
close the final codec/ADC/receiver audio-board integration or release a PCB
for fabrication.

Open [the portable KiCad project](dac_receiver.kicad_pro),
[the routing preview](plots/routing-review.png),
[native top view](plots/top/top.svg),
[native bottom view](plots/bottom/bottom.svg),
[native review](review.json), or [independent handoff](layout-handoff.json).

## Checked construction

- 84 × 64 × 1.6 mm planning envelope; 60 electrical parts and four M2
  clearance holes. This envelope has not been placed in the housing.
- Four copper layers: F.Cu/B.Cu signal and supply tracks; In1.Cu/In2.Cu
  AGND zones. Stackup materials and finished copper are not a fabricator contract.
- 338 segments and 41 conventional through vias. All native DRC, open
  connection, schematic-parity and ERC counts are zero in pinned Linux
  KiCad 10.0.7, with every native check enabled.
- All original E08 component values, footprints and numbered pin nets match
  both the original exported circuit and its independent electrical contract.
  Routing preserves the checked placement, outline and authored zones.
- 34 amplifier feedback/summing connections have continuous F.Cu chains at
  least 0.2 mm wide. The largest sum of whole segments in these chains is
  13.884 mm; the I/V chains reach at most 7.656 mm. This measures construction,
  including segment overhangs, rather than parasitics or stability margins.
- The independent native-polygon screen checks all 41 via drills against all
  SMD lands. Its smallest drill-edge/copper separation is 0.200 mm before
  manufacturing tolerances. Mask, stencil, drill registration and assembly
  acceptance remain separate requirements.

## Integration requirements

J1 retains the **prototype circuit boundary**, with the same pin order as E09.
It is not an approved raw-DAC harness or final product connector. The codec
and its I/V amplifiers must be co-located on the final audio PCB; that work
must reconsider the current J1 routes and recheck the shared ground, ADC
force/sense stars, digital coupling and power distribution. The receiver
region can inform this placement; its present outline and mounting holes
are not the final physical partition.

ESS raw DAC current, DC/common-mode and output-impedance conventions remain
unresolved. The circuit preserves the existing reference-derived I/V gain
without claiming the modeled 2 V RMS normalization is the chip's full scale.
Obtain the manufacturer data and resolve the gain/calibration range before
releasing the integrated design. See
[the existing circuit limits](../../../electronics/dac_receiver/README.md).

Exact passive/connector selections, film-capacitor maximum dimensions and
mounting, ±12 V supply/return behavior, thermal design and enclosure fit still
need review. The 1-second analog/codec settling requirement still applies.
First-article bring-up must keep processed audio muted until qualified;
measured noise, distortion, stability, clipping and fault behavior remain
post-fabrication qualification work.

## Reproduction and evidence

The construction chain is `dac-receiver-stock-01` →
`dac-receiver-placement-02` → `dac-receiver-placement-native-02` →
`dac-receiver-routing-01` → `dac-receiver-routed-native-01` →
`dac-receiver-ground-stitches-01` → this native-refilled project.
`dac-receiver-closed-inputs-01/capture.json` is the native copper capture used
for independent geometry checks. Earlier unsuccessful placement evidence
is retained as earlier revisions and does not support this candidate.

The placement recipe is
[`dac_receiver_layout.py`](../../dac_receiver_layout.py); router interchange
and ground stitching use the existing bounded tools. Native operations use
the pinned, offline Linux container. No Mac KiCad/OpenSCAD process was launched.
No source circuit was regenerated or altered, and no order or upload was sent.

Replay the circuit, native-evidence, placement and feedback audit without CAD:

```sh
.venv/bin/python -m hardware.fabrication.audit_dac_receiver --check
```

These are engineering checks for a development candidate. The complete unit
and this receiver candidate remain unreleased.
