# Sensor ribbon clearance for panel mating connectors

This revision supersedes `harness_pot_clearance/route.scad` for root integration. It retains the full six conditional panel connector receiving envelopes, including their asymmetric latch reservations and Z26.44 top. The earlier ribbon assembly overlapped those envelopes by 14.949934 mm³: 13.107096 mm³ in the cable envelope and 1.842839 mm³ in the clamp/support envelope. The original assembly remains a regression witness.

The first ribbon segment moves from Z28 to Z32, then descends to the main clamp at **(265,69.1891892,28)**. The clamp mounting foot remains D_H2 at (250,57), and its screw/washer seat remains Z23.35. The arm starts at Z22.5 rather than Z21.5 so its longer span clears a neighboring component. The sensor-side clamp, board mounting holes, wiring order and exact connector pin mapping are unchanged. Use `tbh05_harness_complete()` from `route.scad`; do not add the superseded D_H2/D_H5 screw heads separately.

## Assembly length and receiving

The changed route invalidates carrying the old 82 mm precut instruction forward. Start with a **100 mm** 3M3365/06 ribbon blank. Form the cable within the modeled envelope, position both ends against the actual terminal/solder preparation datums, mark each conductor, then trim and terminate. Do not leave a surplus coil in unmodeled space. The longest nominal connector-exit-to-sensor-exit path is80.5781 mm, excluding terminal engagement, stripping/preparation, formed bend allowance and actual packing. These are path estimates, not qualified cut lengths. Reject or revise any assembly that cannot be formed without loading the connector or leaving the reserved space.

The ribbon clamp orientation and forming through the bend remain physical receiving checks; the spherical corridor is a clearance reservation, not proof of bend radius or abrasion life. The longer arm needs a printed strength/grip check. The starting blank's nominal47.5pF/m cable estimate is4.75pF per line. The existing **12pF complete-branch receiving ceiling** and conditional150pF whole-bus budget remain; neither has become a measured acceptance result.

The connector bounds remain conditional project receiving reservations, not supplier-certified mating-stack CAD. This revision accommodates their full frozen geometry; it does not resolve final connector adoption.

## Verification

`trial-r5/review.json` is the selected21-case bounded Linux native run. It checks panel mates, the exact extended pot allocation, all captured board components, shell/controls, sensor carrier, lever motion and fastener seating; four clamp solids must be connected and watertight. `review.py` binds final sources, verifies path continuity, native pin mapping, the original collision witness and printable solids. Root must still repeat the latest combined final-control/guide/fan checks.

`probe-r1` reproduces the old collision and diagnoses its cable/clamp contributions. Its intermediate path contained an overlapping redundant segment; `probe-r2` removes it and checks the continuous path. `trial-r3` found a0.030473mm³ arm/component overlap, retained as evidence. Raising the arm root by1mm fixed that finding in `probe-r4`; the full final batch repeats all affected checks. No physical or fabrication release is implied.
