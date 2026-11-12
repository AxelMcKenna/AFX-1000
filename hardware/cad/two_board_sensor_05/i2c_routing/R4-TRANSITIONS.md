# Local return stitching candidate r4

r4 supersedes r3 for proposed integration. `native-r4/signal_main.kicad_pcb` adds four 0.6 mm diameter / 0.3 mm drill through-ground vias; traces and authored zone outlines are identical to r3. The approved control-return connection at J402.1 remains, with additional local analog-to-digital ground contacts beside MCU-CONTROL signal pins J402.3/.4. This is explicitly a wider control-connector return join, not a pin1-only join. It does not contact the rail-health pin directly.

| Signal transition | Nearest r3 plated return distance | Added ground via X,Y | New distance |
|---|---:|---|---:|
| J402.3, SCL B↔In3 | 5.000 mm | 174.2,85.8 | 1.442 mm |
| J402.4, SDA B↔In3 | 7.500 mm | 175.8,85.7 | 1.442 mm |
| New SCL via B↔In3 | 6.400 mm | 188.460625,83.20625 | 0.860 mm |
| Existing SDA via B↔In3 | 3.739 mm | 187.5,69.1 | 1.020 mm |

These are the nearest legal sites found on a 0.1 mm search grid with 0.2 mm clearance, 0.6 mm via copper and a 0.86 mm existing-via spacing screen. Distances are engineering design choices, not a manufacturer-specified maximum or proof of signal integrity. The close ground vias reduce the return detours at each layer transition without blind-via fabrication assumptions. Both local reference layers are now joined at each transition; no reliance on only distant J402.1 remains.

`transitions-r4.json` binds the native capture and proves each stitch belongs to the same native ground group as D_U1001.20. Each has actual copper contact with the filled In4 and In6 reference planes, plus a continuous 0.2 mm-wide local reference corridor between signal transition and ground via outside the necessary signal antipad. It records exact native UUIDs, positions, old nearest plated connections and every changed filled plane.

The two stitches beside J402.3/.4 also contact the original analog In1 ground plane, at the documented MCU-CONTROL interface. The digital-side stitches contact the existing digital In1/In4/In6 ground fields. Their new through holes require antipads in the digital In2 5 V plane. Native netlist/DRC and full group comparisons remain necessary; these antipads must not be described as unchanged copper. Against original signal03, six filled-zone records change: two new In4/In6 zones, two same-net underlying digital reference zones partially replaced by their priority-1 overlap, digital In1 ground around the new signal via, and digital In2 power clearance around the added vias. Full areas are recorded in the transition report. Existing authored zones remain exact.

Selected checks: `native-r4/review.json`, `return-review-r4.json`, `transitions-r4.json`, and `fidelity-r4.json`. All 116 native polygon conversion cases pass. All 4,826 previously covered track cases retain their reference coverage; all five new paths have adjacent ground reference. Native ERC/geometry are clear, exact schematic net partitions and all original authored objects are preserved, only SCL/SDA/AGND groups merge, and all original groups remain whole. The remaining 246 opens and missing ESS package are unchanged.

No high-current capacity, codec noise, EMC, assembled 400 kHz waveform, or whole-board release is asserted. Final dielectric stackup and capacitance, complete harness, and physical electrical qualification remain open. Reproduce with `stitch.py`, `native_r4.py`, `capture_after_r4.py`, `review_r4.py`, `transitions.py`, `fidelity_r4.py`, and `preview_r4.py`, preserving prior output directories.
