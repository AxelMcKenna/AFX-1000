# Correct C907 reference coordinates

Supersedes the text placement in `ldo_local/inputs-local-return-08`; final corrected board is `inputs-reference-09/power_protection.kicad_pcb`.

The prior text-only correction wrote desired global (184.5,129) into a footprint-local coordinate field. At footprint position (187.5,126.6), orientation 180°, those local values imply global (3,-2.4), outside the board. A clean parity/clearance check did not catch this graphical placement error. Original evidence remains unchanged.

The corrected local reference position is (3,-2.4), which native KiCad must read back as global (184.5,129). The native gate also requires the entire text bounding box inside the board edge bounding box. Five regression tests cover correct rotated coordinates, the mistaken global-as-local case wrong orientation, valid board containment and off-board text rejection. The full board AST permits only this reference-position edit; copper, part pose, pads, nets, fills, text size and all other properties are identical. All materialized bundle inputs except the board are byte-identical to the previous bundle.

Native parity must remain zero with only the four existing DSE errors. All electrical, fabrication and IN/EN completion limitations from `ldo_local/README.md` remain. This remains an isolated candidate, not selected TBP73.

```
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.reference_fix.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.reference_fix.test_verify
```

The first containment check chained a temporary SWIG BOX2I into GetOrigin/GetEnd; this returned invalid temporary-backed vectors. `native_initial.py` preserves that pre-DRC failure. The corrected run retains both bounding-box objects before reading their coordinates; native reports the actual numeric text and board bounds.
