# Private J4 pitch-9 ground-terminal process proposal

Source PCB SHA256: `e7b00fbadc7c61eafe2d4c35489213605c469d73039c831eaf1513f303344a1b`.

Starting from sealed R58 `fed472...`, only J4 changes. Positive terminal remains at housing `(161,120.5)`; its complete copper, drill and mask definition is unchanged. Ground moves from `(161,126.5)` to `(161,129.5)`, with the same 4.2 mm copper land and 2.2 mm nominal plated hole. The matching private library and schematic footprint selection are included. Every track/via, other footprint, zone outline, board edge, stackup and rule stays unchanged. This proposal is not the canonical board.

Fresh all-track/all-severity KiCad checks give **45 opens, zero hard DRC/parity/ERC errors and 76 warnings**. Every per-net open count and every warning type/item UUID matches the frozen starting board. Full native contract comparison changes only J4. Actual filled-force subtraction has no loss above source self-subtraction control; its only 0.0000017373 mm² residual equals that control. These results do not resolve the starting board's opens or qualify the circuit.

Front mask openings are 4.2 mm. The positive backside opening remains 4.2 mm. Only the ground backside pad loses its automatic mask opening and gains an explicit centred 2.6 mm B.Mask circle. Actual exported negative-polarity Gerbers independently confirm this geometry. The backside positive courtyard is 4.7 mm square; ground uses a separate 2.8 mm square tail/solder envelope. Both front courtyards are separate 4.7 mm squares. There is no moulded body between the two wire terminations.

The smaller backside ground envelope is a **process requirement**, not a demonstrated solder result. Combined radial mask-edge error and registration relative to the finished hole must be at most 0.1 mm; finished hole must be 2.1–2.3 mm. At the largest centred hole the exposed backside annulus is only 0.15 mm radially, reducing to 0.05 mm on the worst side under the full offset allocation. Fabricator approval, solder wetting/fillet coupons, mask adhesion and assembler acceptance are absent. Backside solder/tail width must remain within 2.8 mm and projection within 1.5 mm. The 0.5 mΩ solder-joint requirement is unverified.

Native J4's retained part value remains `Alpha3079_AWG14_DIG_FORCE`; no wire BOM substitution is adopted. The proposed 0.7 mm bare-core radius, relative centring allowance and thin-wire route belong to the separate Alpha 6715 study. They are not established specifications of the retained 3079 value. Full actual joint, bare/insulated wire, bore, nearby components, return/positive hardware, case and tolerance checks remain required, along with complete receiving termination, route length, current/thermal and coupled electrical proof.

Five executed native/Gerber negative controls reject a restored full B pad opening, altered ground drill, moved positive pad, off-centre B circle and enlarged actual Gerber aperture. Byte replay reconstructs all final native design inputs from frozen R58 through the three isolated steps. Session preference files and generated reports are excluded from design-byte equality; Gerber generation timestamps are not claimed deterministic.

From repository root, replay into a new directory:

```sh
.venv/bin/python -m hardware.electronics.rail_disconnect.revision28.j4_pitch_replay \
  hardware/electronics/rail_disconnect/revision28/generated/j4-p9-independent-replay
```

The three source generators, native reviewers, raw findings, real mask plots, negative controls and byte-replay evidence are hash-bound in `generated/current-native.json`. No physical, manufacturing, assembly, resistance, startup or production qualification is granted.
