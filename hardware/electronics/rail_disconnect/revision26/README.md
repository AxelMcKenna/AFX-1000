# E26 escape-first board pilot

The frozen pilot has **7,935 segments and 496 vias**, with **21 native open connections, 30 native DRC warnings and zero schematic-parity issues**. The warnings are 29 dangling tracks at still-unconnected escape stubs and one F.Cu copper-sliver warning. The strict checker deliberately fails on these findings; no warning is dropped or treated as zero DRC. All fabrication, physical, copper-loss, current-sharing, startup and build-ready gates remain false.

E26 preserves the 164-part original pin/value circuit, the 156 × 45.25 mm board outline, four mounting holes and six top bulk-capacitor poses. Other component positions change as an explicit new variant; the frozen E25 placement/routing and A11 CAD files remain untouched. The analog 5 V FET pair moves to X=37/46 mm near the source/output headers. Some logic ICs move, and J5 moves to (13, 41.5) mm. The new placement packet requires a new MCAD integration and collision check before claiming fit.

## Routing changes and remaining work

Conventional escapes are reserved before global routing. Resistor via reservations are staggered by ±0.7 mm to avoid the old collinear via fences. IC escapes are staggered where local multiplier capacitors permit. The six Si8751 multiplier capacitor pairs retain short direct F.Cu links. New via placement is excluded beneath the maximum bulk-capacitor body projections.

The initial packet reserves 393 ports and 389 vias. Those are planning reservations, not a claim that every planned drill remains: after routing, 97 native-reported one-face redundant vias were removed. The remaining open stubs and all native findings are retained. Removing redundant drills does not close the 21 missing connections.

The board includes wide source/protected pours and two proposed AGND planes. Analog 5 V pours are 12 mm wide; digital main pours are 8 mm wide. Common-source plates overlap the physical source lands while clearing the gate corners. These widths do not establish resistance, current sharing or ampacity. Actual filled copper, necks, pad spreading, barrel plating, return transfer and worst diagonal digital-current cases still need extraction. No loss-closure claim is made from native connectivity or ideal rectangles.

Power planning requires at least 70 µm finished copper on the relevant layers and copper temperature no greater than 85°C. These are proposed process requirements awaiting fabricator and thermal review. P02 targets the E26 positive/common/protected copper at ≤3 mΩ for analog 5 V and digital 5 V, with separately bounded board returns and ≤1 mΩ common-ground transfer. Its complete source-star return-strap requirement is now ≤2 mΩ, including the bar, hot/end-of-life joints and combined source/E26 board access. The new 2.4 A source reserve does not validate the original E17 fault, timing or late-closure screens.

The original gate/TT/multiplier circuit has no newly guaranteed slew/current limit for late closure into the large bulk capacitors. Inrush, MOSFET SOA, partial-power behavior, thermal/EMI and real audio/assembly measurements remain hard system holds.

## Proposed ground attachments

`attachment-candidates.json` records top AGND landing reservations at (111, 39.5) mm and (128, 27) mm, each 10 × 8 mm, with proposed M3/support envelopes. **They are not implemented in the PCB.** No land, plated stud hole, joint process, busbar route or backside keepout is approved by that file. A nut or 20 mm² busbar cannot be assumed to fit the original 0.3 mm underside gap. A new support/floor/busbar integration must prove it.

## Reproduce and inspect

```sh
python3 -m hardware.electronics.rail_disconnect.revision26.replay --check
python3 -m hardware.electronics.rail_disconnect.revision26.replay
python3 -m hardware.electronics.rail_disconnect.revision26.check --kicad-cli /path/to/kicad-cli
```

The replay exactly restores the frozen pilot bytes. It does not approve the board. The final strict check is expected to fail until the 30 DRC warnings are resolved; `--require-closed` additionally rejects the 21 open connections. `generated/pilot-findings.json` records the actual native counts and failure scope, alongside the unfiltered `drc.json`, filled board, placement packet and native SVG views.

`generate` and `wire` retain the experimental escape-first construction workflow. They begin a new unqualified routing attempt and invalidate prior verification. `cleanup` only removes vias specifically reported by native KiCad as one-face redundant drills; it never changes a pad, pin, value or net. Every change requires a fresh native check.
