# R83 manufacturer copper-land candidate

This separate E13 candidate implements the Bourns CRT0805 recommended copper
lands for the proposed 127 Ω precision resistor. The selected
`rail-monitor-reserved-closed-native-02` board remains unchanged.

The [fresh native review](review.json) reports zero DRC findings, zero uncapped
opens, zero ERC findings and zero schematic-parity findings, with all native
rule categories enabled. The review ran in the approved pinned Linux KiCad
10.0.7 image. It refilled only this new candidate and preserved the source.

The [independent comparison](r83-land-review.json) establishes:

- All original component values, pin nets and placements remain exact.
- Only R83's footprint identifier, two copper lands and courtyard changed.
- All existing tracks, vias and authored zones remain exact.
- Rectangular copper lands are 1.00 × 1.35 mm, centered at ±1.00 mm, giving the
  recommended 1.00 mm inner gap. The courtyard extends to ±1.75 × ±0.95 mm.
- All 357 existing via holes remain outside SMD copper. The conservative minimum
  hole-edge-to-SMD-copper gap is 0.110121957 mm, including the revised lands.

The land dimensions were independently checked against page 2 of the
[Bourns CRT manufacturer sheet](https://www.bourns.com/docs/product-datasheets/crt.pdf),
revision 01C, SHA-256
`094e3bd73684274232f29cce9861062555f18e8316d0c974fe295f4adee46457`.
The candidate body maximum is 2.15 × 1.40 × 0.65 mm. The copper-land drawing
was visually reviewed before transcription.

The proposed order code **CRT0805-PT-1270ELF** is derived from manufacturer
syntax; its exact supply configuration and availability remain unconfirmed.
The existing [resistor selection review](../../parts/rail-monitor-resistors-01/README.md)
also retains the installed 0.1% total-error requirement and the post-reflow
measurement/process question. This geometry result does not close those items.

Mask, paste, stencil, registration and assembler acceptance remain open. The
drill gap is a geometric screen, with actual fabrication tolerances still to
be received. The earlier mechanical and PDN reviews cover their own saved
boards; they are not inherited by this footprint revision. No 3D model or
physical assembly has been qualified for the new part.

Construction is recorded in
[the separate source candidate](../rail-monitor-r83-land-01/construction.json).
The portable native project is [rail_monitor.kicad_pro](rail_monitor.kicad_pro).
Neither candidate is selected or released for fabrication. No parts were
ordered and no external message was sent by this board change.

The independent check can be replayed without native CAD:

```sh
python - <<'PY'
from hardware.fabrication.audit_rail_monitor_r83 import check
report = check()
assert report['native_counts'] == {
    'violations': 0, 'unconnected_items': 0, 'schematic_parity': 0, 'erc': 0,
}
print(report['minimum_drill_to_SMD_gap_mm'])
PY
```

The constructor and native review write new directories and refuse to overwrite
existing evidence. Mac CAD remains disabled.
