# Private E28 routing and return-copper draft

This is a development candidate, **not a build or fabrication release**.
The canonical E28 board and sealed U14 source remain unchanged.

Fresh KiCad 10.0.7 checks report **32 opens, 82 warnings, 0 hard DRC,
0 schematic parity findings and 0 ERC findings**. The sealed U14 baseline has
43 opens. No severity, clearance, drill or other rule was relaxed.

Only U23/C68, U26/C71, U27/C72 and U28/C73 move into the explicit added routing
band. C72 changes from F to B using the existing standard B-side 0805 pattern;
all logical pad identities and nets remain equal. The three south-edge objects
extend to board Y54.5/world Y163. All ports, studs, bulk capacitors, mounting
axes and force-zone primitives remain fixed. The ten added AGND zones comprise
eight inner-layer band extensions and two low-priority return reinforcements
on F/B, board X120..154, Y16..40. Their parasitics and assembly implications
remain unapproved. All 5,592 original operative locked copper objects remain
exact. The exact delta records 69 removed obsolete copper objects and 2,435
new copper objects; it also records every other changed board object.

The current interface remains U14/P9: J4 ground is world Y129.5. The separate
fed/EI02 accepted-wire source uses world Y126.5. The J8 lug and PB02 proposal
are **not adopted**, and no accepted wire-route or physical-fit evidence is
inherited. Historical numeric/mesh placement screens retain their actual
source identities; a fresh complete MCAD integration is still required.

Actual filled geometry, native pad polygons and distributed finite barrel
walls produce these diagnostic estimates under unaccepted 70 µm per-layer,
85 °C, 25 µm minimum plating and contact assumptions:

| Path / extra copper term | Grid | Diagnostic |
| --- | --- | --- |
| Analog positive, extra above 20/3 mΩ chips | 0.05 / 0.025 mm | 2.952091 / 2.938267 mΩ |
| Digital positive, extra above 20/4 mΩ chips | 0.05 / 0.025 mm | 2.524418 / 2.497061 mΩ |
| J4.2 F-contact to J8.1 top stud | 0.05 / 0.04 mm | 1.772380 / 1.772989 mΩ |
| C20.2 B-contact to J7.1 top stud | 0.1 mm | 1.973776 mΩ |
| C24.2 B-contact to J8.1 top stud | 0.1 mm | 2.005762 mΩ |

The capacitor rows explicitly retain the PCB charging/return loops. These
numbers are not resistance upper bounds or full-strap passes. External bars,
bolted/soldered contacts, P03 multiport ground, capacitor ESR/leads, dynamic
loads and complete thermal/startup/fault behavior remain outside these rows.
The retained bipolar hard-disconnect/inrush problem and first-master full-load
thermal/SOA checks remain open. All physical, fabrication and release flags
remain false.

`generated/preservation-review.json` checks source preservation.
`generated/force-integer-review.json` shows the two new outer ground patches
preserve every native integer force contour exactly relative to the 32-open
routing source. The earlier routing-stage contour differences remain recorded
in that stage and are not erased by this comparison.

The literal delta is a byte-replay recipe, not an electrical-correctness proof:

```sh
.venv/bin/python -m hardware.electronics.rail_disconnect.revision28.literal_board_delta replay \
  hardware/electronics/rail_disconnect/revision28/generated/p9-u14-input-escape-work/rail_disconnect.kicad_pcb \
  hardware/electronics/rail_disconnect/revision28/generated/u28-return-dual-plane-work/generated/U14-to-draft-delta.json \
  /private/tmp/e28-new-replay.kicad_pcb
```

The output path must not exist. The replay must produce SHA256
`dd6a6f5adab873526234818c1b4274925e8c8e75b9cfe34be1ca9f258753e5ec`.
Changed-source and changed-literal negative controls reject before writing.
Raw native reports, filled source, actual native pads, solver results and logs
remain under `generated/`; no findings have been suppressed.
