# Sensor workflow adapter

`components.json` exports fourteen atomic component roles through the zero-argument modules in `sensor.scad`. Geometry stays in its frozen source modules. The root assembly should instantiate each role once and use these IDs for dependency-driven checks.

The fixture includes carrier, cap, guard and fasteners; the substrate and actual populated-board envelope are separate. Do not also instantiate the aggregate `tbh05_installed()` or its generic `sensor_package()` reserve. The actual-population module already includes the solder/local-wire reservations. The sensor harness is the corrected `harness_mate_clearance` revision from83cab01c, with its clamps and replacement screw heads included.

D_H2 and D_H5 retain their mounting holes but replace the original board-seat screw heads. Their new washer/head seats areZ23.35 andZ18.35 respectively. Keep the source board substrates and standoffs. Do not duplicate the old screw heads under the clamps. The fixture's shared lever bolts also retain the existing carrier's documented M3x25 stack.

Intentional contacts are explicitly labeled by kind. They are not blanket permission to skip all geometry between the named components: PCB edge seats, component solder attachment, cable termination region and spring attachments need their established checks. The motion roles include continuous sweep envelopes; they are not printable static solids. Full-source native evidence remains authoritative for the detailed seating and body-clearance checks.

`build.py` regenerates the registry from frozen sources; `validate.py` verifies exact thin delegation, recursive source hashes, called-module presence and selected PCB hashes. No new CAD shape, clearance claim or electrical design is introduced. The selected main signal PCB remains input-r7; unverified DAC candidates are deliberately absent. Root owns the unified render and affected-check runner.

## Nominal installed lever view

The adapter now exposes the zero-angle rotor translated byZ7.6, both pivot shims, the nominal shaft, the rightX326 screw heads and the fixed/moving spring pins. LeftX306 screw heads remain solely in the fixture role. The pin module includes bent split-pin receiving boxes; its uncertainty records this mixed representation explicitly. Motion roles intentionally contain the nominal pieces and should be rendered as overlays, not added printable material.

No frozen nominal magnet or grub-screw solid exists. The registry lists these as unmodeled installed items; the displaced `magnet_escape()` diagnostic is not reused as an actual magnet. The nominal spring body is a receiving hull, not actual coil geometry. These omissions remain visible instead of being hidden by invented parts.
