# Touch cradle removal diagnostics — not a release-qualified design

These studies move the **entire mated receiving box** out of the cradle after
removing its strap. They do not model connector halves unmating. The prescribed
24 mm Y translation exceeds the reserved 23 mm body length by 1 mm; neither this
choice nor the JST catalog's 21.35 mm reference mated length establishes actual
engagement or unmating travel. The old r1 source comment referring to a released
latch/mating axis was an unsupported interpretation and is superseded here;
that exact source is retained to bind the native witness.

| Study | Motion | Local result |
|---|---|---|
| r1 | Y +24 mm | PCB population collision 84.252887 mm³ |
| r2 | Z +3 mm, then Y +24 mm | Population clear; installed controls collision 32.871863 mm³ |

Both positive sweeps are closed native solids. Both studies clear the checked
sensor and ground/support geometry. R1 clears controls. R1 population witness
bounds are [174.45,145.25,21.5]–[183,160.5,23.36], intersecting N_U22 and N_J2
receiving allocations. R2 controls witness bounds are
[172,130.142654,33.200001]–[176.100006,135.874847,35.5]. The six degenerate
triangles in this small controls witness are reported in the native mesh audit;
after their exclusion the directed boundary is closed. No interference is
waived. These failures **do not prove actual connector release is impossible**.
A lid-removed procedure may remove the controls obstruction but has not been
verified as a complete service sequence.

`slack_audit.py` binds all eight fixed-end wire halves from r29. For each
piecewise-linear cradle motion it evaluates the maximum Euclidean endpoint
separation at motion vertices (distance is convex along each interval). All
halves pass this necessary length bound; the smallest excess is 13.528638 mm.
A shortened-wire mutation fails. This is **not** a constant-length deformation,
curvature or collision proof. Translating the whole wire moves its soldered
endpoint; shortening a straight removes physical length. The outgoing TH1,
TH2 and TH4 first straights are shorter than 24 mm, so naïve shortening also
crosses their first bends. A real deformation must store slack, maintain R13,
keep both endpoint registrations, avoid every wire and obstacle throughout
motion, and avoid loading the solder joints.

Open prerequisites: controlled/measured connector mating axis, engagement,
latch and gripping envelope; delivered body bearing surface under the cradle
strap; strap cutting/removal access; source and module termination strain
relief; constant-length wire deformation and service sequence. No completed
touch wires or root selection is claimed. Exact JST drawing access remains
gated; no supplier was contacted and no personal information was submitted.

Run the two host audits:

```
.venv/bin/python -m hardware.cad.two_board_installation_06.r32_touch_release.slack_audit
.venv/bin/python -m hardware.cad.two_board_installation_06.r32_touch_release.verify
```

Ten native results retain transitive source hashes and artifact hashes. R1
sources are preserved under `rejected-r1`; current sources reproduce r2 with
the bounded pinned Linux runner. No new physical geometry is selected.

Self-review corrected the conflation of full-cradle removal with connector
unmating, and added both host and C3 fixed-end length checks rather than
assessing only the outgoing halves. Length sufficiency, motion clearance,
actual mating compatibility and assembly qualification remain separate.

## Restricted constant-length deformation

`bend_family.py` supplies an exact analytic deformation of the four **host-side
halves only** with their source exits fixed. For a pure +Y connector translation
`t`, increase the downstream quarter-circle radius from 13 to
`13+t/(2-pi/2)` mm and shorten both adjacent straight runs accordingly. This
preserves wire length and both terminal tangent directions, with radius never
below 13 mm. The first straight reaches zero at a common four-wire travel limit
of **10.874447 mm** (individual limits 10.874447, 12.171042, 12.402812 and
11.569757 mm). The identities and nonnegative straight lengths are checked at
101 points per wire, including both endpoints.

This family cannot achieve the prescribed 24 mm whole-cradle removal. That is
not a proof against other deformation families. No swept clearance, mutual
wire separation, outgoing-half constant-length deformation or Z-lift is
verified. In particular, the increased radii change the corridors, so the
installed r29 clearance results cannot be reused for this motion. Actual
unmating travel remains unknown and is not set to the analytic family limit.
