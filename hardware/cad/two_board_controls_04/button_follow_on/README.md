# Twenty-five button-indicator receivers

**Guide correction:** use `../connected-guide-r1` final guide exports and `../connected_guide.scad` integration wrappers. Earlier guide exports remain historical because their ring relief left a loose central island. The final guides are each one connected solid; all50 button seats remain verified.

Twenty-five Kingbright KPT-1608CGCK emitters now have actual routed boards, retaining interfaces, wire exits and unobstructed paths to the existing button caps. They preserve channels 0–24 and all existing button locations, mounting holes and 1.2 mm travel. This green population establishes a concrete optical-fit candidate; final colors, brightness and diffusion still require acceptance. Use the retained key geometry in translucent material. An opaque cap will not become illuminated merely because an LED is beneath it.

## Parts and assembly

Use **0.6 mm PCBs**, not the usual 1.6 mm stock. Build 8 vertical boards, 2 horizontal boards, 10 scene boards, 3 pad boards, 1 pad1 board and 1 vertical_top board. `contract.json` assigns each to its named control; only QUANTIZE uses vertical_top. Each board carries one specified LED and two direct-solder wire pads. W1 is cathode, W2 is anode. The source manufacturer drawing remains at `../led_follow_on/reference/KPT-1608CGCK.pdf`; pad polarity and recommended geometry are implemented explicitly.

1. Print the new full or split guide, with its shallow PCB pockets facing the lid. Keep the final ring-follow-on lid; button LEDs add no new lid holes.
2. Seat each board at Z42.9–43.5, emitter facing up. The guide leaves 0.7 mm beneath the PCB and provides a 0.7 mm deep pocket with 0.2 mm side clearance. The moving stem retains its original guide opening.
3. Place a 0.1 mm insulating PET washer at each mounting hole, then install the existing M2×8 countersunk holder screws into the checked/tapped printed Ø1.6 pilots. Fifty custom washers, OD4.2/ID2.4, are provided as a cut-sheet SVG. These washers close the nominal 0.1 mm gap above the boards. Measure the actual PCB/guide stack and adjust shim thickness to clamp without bowing the board; do not force screws to compensate for interference.
4. Feed the soldered leads through the Ø2 guide exits. The modeled Ø1.5 reserves include solder and the first 2.5 mm below each board. Insulate exposed joints. Full routing, strain relief, connector/crimp choice and anode distribution are a separate harness task.
5. Use translucent versions of the 25 existing illuminated key shapes. TAP, NUDGE± and BANK remain unlit because they have no assigned LED channels. Check cap visibility, uniformity, legend contrast and return over the full stroke before accepting the optical assembly.

The LED center is local X4.8/Y0. Maximum body top is Z44.35, leaving 1.25 mm below the cap underside at full depression. The retained clip's nominal top is Z42.2; PCB bottom is Z42.9. Actual stack tolerances remain receiving measurements. The existing switch, spring, compliant puck, clip and tapped-holder retention requirements remain unchanged.

## Evidence and integration

`pcb-native-r3` records zero DRC violations and zero opens for all six distinct board designs. Cathode and anode pin groups are checked natively. `planar-review.json` checks all 300 installed PCB pairs and proves every mounting pattern matches the original holder contract. `wiring.csv` maps all 25 cathodes and 25 individual anode leads against the integrated signal PCB, including exact exit coordinates. Do not put multiple anode leads into one connector crimp; use rated distribution/splices selected by the harness owner.

`native-r5` passes nine empty geometry/preservation cases, four positive optical/retention cases, and three guide print meshes. Positive volumes assert that all 25 light columns reach their caps at both travel endpoints and all 50 board mounting seats provide support and capture. Only the intended seating plane receives a 0.01 mm guard. Exact preservation is checked at both constant-thickness guide layers; the earlier 3D symmetric difference's 4e-7 mm³ numerical sliver is retained as historical evidence, not reported as empty.

Integration modules in `buttons.scad`: `tbh07_installed()`, `tbh07_guide_variant()`, `tbh07_lid_variant()`. The lid wrapper preserves the frozen RGB-ring lid. The new guide inherits every earlier display, selector, meter, bank and ring modification. Actual captured part dimensions, LED footprints and source hashes remain reviewable.

Earlier failures remain historical: QUANTIZE's lower wire exit touched a nudge-holder post; a scene bridge grazed a ring support; the top-exit layout needed a larger cathode-pad routing keepout. All were fixed without moving the buttons or changing sealed earlier carriers. No physical or optical acceptance, whole-panel schematic ERC, or fabrication release is implied.
