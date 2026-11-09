# Inlet jumper comparison inputs

[JST VH manufacturer catalog](JST-VH-2026.pdf) was downloaded from
[JST's regional catalog](https://jst.de/file/download/1036/vh-connector).
PDF metadata records creation on 9 January 2026. Pages 3 and 4 were rendered
and inspected for the standard B2PS-VH header and its mated dimensions;
pages 5 and 6 confirm model naming and omitted-post variants.

The standard AWG16 connection is catalog-rated 10 A. The catalog gives
10 mΩ maximum initial and 20 mΩ maximum post-test contact resistance.
A two-conductor jumper with two connectors has four mated current-carrying
contacts: its contact-only screen is therefore 40/80 mΩ, before wires,
crimps, pads and source connections. At the existing conditional 4 A input
profile, that is 0.16/0.32 V and 0.64/1.28 W distributed across the four
contacts. These are conditional arithmetic screens, not measured unit limits
or predictions of equal contact heating.

A conservative side-entry receiving box of 9.86 × 25.35 × 11.5 mm was used
for initial placement exploration. This is a project reserve, larger than
the catalog's nominal 20.5 mm mated depth and 10.5 mm height; it is not a
manufacturer tolerance specification. The retired inlet position at
(292, 29.4), angle 0, clears that limited envelope check. A 1 mm-grid search
near the lower protection area found no receiver position without component
conflicts; this does not prove that another orientation, a repack or another
connector cannot work. Cable routing, crimp validation, bend radii, strain
relief and full installed fit were not established.

The next authored PCB candidate instead uses parallel feed/return copper
corridors. That choice avoids introducing an unverified cable assembly and
receiver repack, but leaves corridor constrictions, via transitions, copper
thickness, temperature rise and complete source/fuse coordination to verify.
Neither the jumper nor the corridor is released for fabrication by this note.
