# J8 attachment: private receiving-gauge study

**Current hardware fails the declared complete-attachment screen. No PCB, BOM, ground strategy, part, process or physical qualification is adopted.**

Source is the immutable U14/P9 PCB `28c86cea474e46e9b857c11c059f304b8e61f46444d87b8aabcfc50f2b81c945`, with 43 opens, zero hard DRC/parity/ERC and 66 warnings. Fresh component extraction includes both actual PCB faces. Copied bar/support meshes are new obstacles in these checks; their prior passes are not inherited.

Phoenix 3240070 drawing: external unmodified manufacturer PDF SHA `298dfeae7e889b60ebda6a0f73a22e4d1c8088fc0e80fec8865d1b0492276f9e`, public [original-document mirror](https://assets.alliedelec.com/image/upload/v1560335573/Datasheets/7eaee44fb49a5f530b06013ed722fd87.pdf). All three pages were rendered and visually reviewed. Nominal ring width 6 mm, overall length 14 mm, barrel length 5 mm, barrel bore 1.6 mm, ring-centre to barrel start 6 mm, ring bore 3.2 mm and stock 0.8 mm are dimensioned. Barrel OD/height, transition profile, tolerances and finished crimp envelope are not. Current official text calls the stock dimension a **minimum**. The original copyright remains on the external PDF; it is not redistributed here.

`receiving-requirements.json` therefore defines a **project receiving gauge, not vendor-maximum CAD**. Its 5 mm maximum outer crimp width/height, 1 mm maximum flat stock and other limits require actual supplier/assembler acceptance and inspection. Exact die, tinned fine-strand compatibility, insulation, strain relief, post-crimp wire axis, tool recipe, usable thread and contact resistance remain unresolved.

The physical stud centre is housing `(132,129.5)`, not its custom-pad anchor at X+3.3 mm. The lug lower receiving plane seats on the existing DIG bar at Z15.1. With 1 mm gauge stock, existing maximum washer thickness 0.55 mm and 6 mm diameter/2.52 mm head height, the head top is Z19.17. The nominal-length engagement example is `8−3.57−1−0.55 = 2.88 mm`; it is **not** a guaranteed minimum because screw length tolerance and usable stud depth are not accepted. The whole lower lug plane is the intended bar contact. Independent float is not applied twice across this common mating plane; its electrical joint resistance remains unqualified.

At −20° the lug envelope collides with both positive-link envelopes and the analog return bar. Clocks −90°, −120° and −150° also fail. At **+90°** (southward):

| Actual native check | Result |
| --- | --- |
| Lug, inflated by ±0.65 mm relative position + 0.25 mm clearance, against electronics / positive links / returns | All empty |
| Complete lug + washer + head with the same inflation, against electronics / returns | Both empty |
| Complete inflated attachment against current positive links | **2.100254 mm³ collision** |
| Complete uninflated attachment against electronics / positive links / returns | All empty; nominal geometry only |
| Deliberate overlap witness | 0.008000 mm³ detected |
| Known rejected clock against actual positive links | 80.959878 mm³ detected |

The failed complete intersection spans approximately X128.912..135.088, Y125.10..125.87, Z17.48..19.52. A nominal fit does not replace the failed inflation screen. Root owns the separate, unaccepted positive-link proposal moving only DIG corners `(110,122.3,17.8)` and `(143,122.3,17.8)` to Y121.3. No corner, bar or other root-owned source is changed here.

## API for the separate bar comparison

Create a driver beside the captured `gauge.scad`:

```scad
include <gauge.scad>
module proposed_positive_obstacles() {
    // Import the actual proposed complete covered DIG envelope and all
    // unchanged ANA/support/fastener obstacles; retain their dimensions.
}
intersection() {
    expanded() { lug(); washer_head(); }
    proposed_positive_obstacles();
}
```

Run the verified native executable with the declared receiving bounds intact:

```sh
/private/tmp/rmx-openscad-mounted/OpenSCAD.app/Contents/MacOS/OpenSCAD \
  --hardwarnings --backend Manifold --export-format binstl \
  -D 'part="root_variant_compare"' -D 'angle=90' \
  -o /private/tmp/j8-proposed-positive-collision.stl /path/to/driver.scad
```

`part` disables the included historical cases. `angle=90` sets the actual proposed clock. `expanded()` adds the 1.8 mm centred cube once. `lug()` is the receiving envelope; `washer_head()` includes the new complete stack above its maximum stock. `shaft()` is checked separately through the minimum receiving bore. `own_bar()` is the intended mating bar. Every free-neighbor check, controls, whole wire, case, panel poses, supports and receiving terminal still needs its own source-bound proof.

`captured-native-replay.py --openscad /path/to/OpenSCAD` replays only captured geometry into a new scratch directory. `native-replay.py` instead refreshes extraction from live repo sources before checking. All original failures and recipe bytes are retained in `first-run-before-style.tar.gz`, with decompressed-byte index. No numerical resistance, startup/SOA or wire route is inherited.
