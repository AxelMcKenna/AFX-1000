# PB02 digital-link mid-leg proposal

Two digital copper-link centreline points move from Y122.3 to Y121.3 mm.
Every electrical port, analogue path, other digital point, material dimension,
insulation, cap, fastener and support definition remains fixed. The digital
centreline shortens from 172.5 to 170.5 mm. This is a separate development
proposal; the original positive-link kit and all parent evidence remain intact.

Actual CAD outputs include the [digital copper STEP](generated/DIG-CU.step),
[copper mesh](generated/DIG-CU.stl),
[covered receiving envelope](generated/DIG-COVERED-ENVELOPE.step) and
[assembly STEP](generated/positive-links.step). Files retain assembly coordinates.
`generated/geometry.json` binds all 32 valid BREP parts and source identities.
These exports do not establish manufacturing process, insulation or electrical
contact qualification.

The complete south-facing J8 receiving lug, washer and head now clear the
new positive hardware under the original ±0.65 mm free position and 0.25 mm
external clearance, plus the positive hardware's separate ±0.1 mm position.
The direct native screen and an equivalent empty-intersection screen agree.
The latter moves the symmetric box dilations onto the simpler lug geometry:
intersection existence for `(A + box(.9))` and `(B + box(.1))` equals that for
`(A + box(1))` and `B`. It makes no intersection-volume equivalence claim.
Both methods reproduce the old 2.100254 mm³ collision; a 0.008 mm³ control is
detected. See [the three-case equivalent screen](gauge-screen/verification.json).

The completed PB02 neighbour, control, case, support and separate U14 component
screens clear. The original positive-wire route fails the maximum covered-link
screen by 3.880921 mm³ at X190.194–193.170, Y109.830–117.170, Z24.247–24.620.
That region is outside the two shifted mid-leg points. The failure is retained;
the old nominal-kit wire result cannot approve the larger receiving envelope.

The [revised positive wire](wire-raise-1mm/verification.json) translates every
curved middle point up exactly 1 mm and extends both vertical insulated ends
by 1 mm. All nine native follow-up cases pass, including the covered positive
hardware, electronics, PS01 bodies, controls/case, return/mount hardware,
the unchanged negative wire and J8 attachment. Source/receiver bare and joint
geometry remain fixed. Independent review ties the actual path back to its
selected analytic curve certificate: the minimum radius remains 9.7 mm and
the length bound increases from 85.191 to 87.191 mm. Cut slack, forming,
strain relief and a new resistance bound remain unqualified.

All 32 exported part/envelope meshes are independently closed, oriented and
free of zero-area triangles. Sixty-eight finite minimum-stock section witnesses
meet the existing 6 mm² requirement; the smallest witness is 6.1444 mm².
The main native receipt retains two false statuses for literal-import outputs
that do not emit Manifold's `NoError` message. `review.json` names just those
exceptions and independently proves exact source-mesh statistics, strict
topology and agreement with BREP volume. It leaves the real old-wire failure
rejected. No blanket log or volume waiver is applied.

The captured EI02/PS01 scene uses E28 `fed47258` and its old J4 return
at Y126.5; the separate U14 component screen uses `28c86cea` with J4 return at
Y129.5. These contexts do not constitute one coherent assembled wiring design.
The J8 outgoing return has no newly designed wire or strain relief here and
does not remove C24 charging or load-step return currents in the PCB.

The first failed snapshot attempt is retained under `history/`; its commands
stopped on a missing transitive CAD library and produced no fit result. The
current capture closes the literal include/use/import graph, adds the Trill and
repaired-component libraries omitted from the flat PS01 maps, and byte-checks
the complete 241-member J8 source archive. Sources remain frozen while native
jobs run.

`sections.py` renews finite local minimum-stock BREP section witnesses and a
conditional uniform-section copper resistance estimate. Those samples cannot
prove a global minimum section, three-dimensional current crowding, actual
conductivity, joint resistance or the complete 2 mΩ link target.

No PCB ground strategy is adopted by this proposal. All physical, electrical,
thermal, process and fabrication release approvals remain false.
