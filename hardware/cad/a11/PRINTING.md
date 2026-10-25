# RMX A11 — printer handoff

A11 integrates the in-progress 90 × 44 mm higher-headroom supply board at (201,105,6.5) mm. This is separate from the B1 budget hardware. The supply has 157 individual courtyard reserves with conditional body heights; bottom capacitors leave only 0.35 mm allocated floor clearance. Confirm actual component heights before printing the full chassis. M2 power-board fasteners, underside retention and feet remain unselected.

All model dimensions are millimetres. Import at 100% scale. This is a complete inventory of the modeled printed housing/control parts, with nominal interfaces ready for prototype printing. It is not a measured or physically qualified finished product.

## Files to use

- `RMX-A11-complete-print-inventory.3mf` contains separate named objects and the full part quantities, plus two test coupons. It uses a 750 mm wide nonoverlapping inventory layout so the whole order can be inspected together. This is not a machine profile or G-code. Rearrange the parts onto the actual machine's build plates; do not scale the master layout to fit a printer.
- `STL/` contains one file per distinct design. **Use `parts.csv` for quantities.** Do not print just one of every STL and assume the set is complete.
- `CAD/assembly.scad` is the editable source and assembled reference. Do not print the assembled unit as one fused solid. The assembly includes purchased-component and clearance references.
- `cad-overview.png` shows the assembled unit, exploded mechanism, part families and button section. Colours distinguish parts and are not a validated optical/material specification.
- `validation.json` and `manifest.json` record geometry checks, source hashes and file checksums.

The largest part is the 334 × 157 × 38 mm chassis. The front panel is 2 mm thick and the guide plate is 1.4 mm thick. Confirm machine capacity and process suitability for the thin guide plate, snap clips, lettering, small light pipes and pilot holes before quoting. Every STL has its print face at Z=0; some retain local XY offsets. The 3MF normalizes and arranges all copies. The exported print orientation is intentional. The lever may require supports; slicer support settings are not prescribed by the CAD.

## Print and fit order

1. Print the panel and shaft fit coupons, one representative rectangular key, one sector key, their holders, and several retaining clips. Measure the actual shaft, switch case and slider actuator before a full run. The nominal shaft socket is Ø6.2; the coupon has Ø6.0/6.2/6.4 samples. Clearances are model dimensions, not compensation for a specific printing process.
2. Print the opaque parts in a tough process/material suitable for the clip and switch-case retention lips. Optical parts are separate transparent/translucent items. Choose those processes with the printer; strength, friction and optical transmission have not been measured.
3. Install switches into the insulating holders, using the four 1.2 mm lead holes on a 6.5 × 4.5 pattern. The holders are plastic, not PCBs. Switch leads must be connected by separate wiring or an appropriately designed circuit; do not attempt to solder to the printed carrier itself. Keep wiring within the allocated lead clearances.
4. Place each key through the front panel and D-guide opening. Insert its silicone contact, return spring and retaining clip. Fit the matching holder from below, then secure its two posts through the panel/guide plate with M2 screws. The pad-1 holder has both posts forward of the USB reserve; the quantity schedule identifies its separate shape. The guide's flat prevents cap rotation.
5. At rest the cap underside is 1.2 mm above the panel. At full nominal travel it meets the panel and transfers finger load to the lid. Check electrical closure before this stop, contact compression, free return, lateral play and clip retention. Do not trim away the stop or replace the compliant contact with a rigid plunger.
6. Fit the touch backer and 0.8 mm lens. Fit the ring lens, bank light pipes, meter bars and display window; their flanges locate against the panel and need a compatible removable adhesive/retention process. Electrode foil attaches to the underside of the touch lens, separate from the printed parts. Verify sensing and optical isolation before accepting them.
7. Fit the pots and knobs after measuring shaft projection and bushing/nut height. The knobs seat 2.8 mm above the panel for nut clearance. The blind socket is 10 mm deep; verify adequate engagement with the selected shaft length. Tap the radial Ø2.5 pilot M3 and use the recessed access bore to tighten the grub screw against the shaft's flat. Fill the pointer/lettering grooves with paint if desired.
8. Fit the two selector caps onto the nominal 1.5 mm square actuators; their 1.7 mm square sockets and the panel openings accommodate the JS switch travel. Confirm actuator engagement and end detents with the actual parts.
9. Assemble the lever, pivot, magnet and return spring. Check its complete 0–35° stroke, return, axial retention and sensor alignment. Close the chassis only after all wiring, mating connectors and live mechanical travel clear it.

## Purchased / separately fabricated hardware

| Item | Quantity | Nominal interface / role |
| --- | ---: | --- |
| Omron B3F-1000 tactile switch | 29 | 6 mm case; 4.3 mm nominal height; seating Z=27.2 |
| Button return spring | 29 | Custom nominal design below; spring supplier approval and force test required |
| Soft silicone contact | 29 | Ø3 × 2, retained by a Ø2.8 blind pocket; actual hardness/compression must be tested |
| M2 countersunk screw | 58 | Nominal M2 × 10 for the holder posts; tap/check Ø1.6 printed pilots |
| M2 pan-head screw | 4 | Nominal M2 × 4 for the touch backer; check tip clearance |
| M3 pan-head screw | 6 | Nominal M3 × 10 for the front panel; tap/check Ø2.5 chassis pilots |
| M3 pan-head screw + hex nut | 4 + 4 | Nominal M3 × 10 rear fixings, with 5.7 mm across-flat nut pockets |
| M3 grub screw | 10 | Nominal M3 × 4 for the knobs; radial access is recessed |
| Potentiometers | 10 | PTV09A-6 family reference; select the 6 mm shaft style, projection and mounting hardware to match the socket |
| C&K JS202011CQN / JS203011SCQN | 1 each | Default/User and three-position Release selectors |
| Lever pivot | 1 | Ø3 shaft; verify final length and positive axial retention in the assembled bracket |
| Lever magnet | 1 | Ø6 × 2 diametric magnet; check fit/retention in the Ø6.2 socket |
| Lever return spring, pivot retention and washers | 1 set | Fit to the modeled eye/shaft; select against measured travel and return load |
| Optical adhesive/mask, electrode foil, wiring | As required | Separate from the printed parts |
| Electronics, PCBs, connectors, feet and power hardware | Separate build | The print pack is the enclosure/control mechanical set, not an electronics kit |

The button-spring design target is OD6.0, ID5.4, Ø0.3 wire, 4.5 mm free length, two active turns with closed end turns and solid height no greater than 1.2 mm. Target rate is approximately 0.2 N/mm, with roughly 0.3–0.5 N return force over the nominal installed stroke. These are design/selection targets, not a stock part number or a measured fatigue/force qualification. The spring seats on the switch cover, so its bearing ends and cover loading must be checked. Use measured insulating shims if needed; any shim changes contact gap and spring preload.

The release spring, shaft retention and magnet adhesive remain purchased-part selections rather than printed substitutes. None of the native mesh checks establishes material strength, button feel, electrical performance, full-unit wiring, production tolerances or live-use acceptance.

A11 adds four E25 floor mounts and local guide/inner-ledge relief for C24 vent air. E25 electronics are UNROUTED and unqualified; the source-harness trial does not meet the 5 V loss budgets. The print pack is for mechanical review.
