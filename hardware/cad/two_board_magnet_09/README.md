# Magnet and pivot screw geometry candidates

This adds the missing nominal parts without changing the accepted assembly or
frozen sensor CAD. These are engineering candidates, not purchased or qualified
hardware. Candidate manifests are for checks; they contain original and revised
alternatives and must not be used as a nonduplicated installed scene.

The existing contract requires a diametrically magnetized Ø6 × 2 mm disc.
[AMF part 93201](https://amfmagnets.co.nz/products/neodymium-disc-6mm-x-2mm-diametric-n35)
is a matching nominal N35 candidate. Its dimensional tolerances, field at the
sensor die, coating/adhesive compatibility and receiving acceptance have not
been established. No axial magnet is substituted. Supplier page inspected
2026-11-13; category-wide property tables are not treated as product guarantees.

The first model seats the nominal magnet at X305..307 with a proposed0.1mm
adhesive film against the existing X307.1 pocket floor. Its nominal package-face
gap is1.95mm, not the old zero-film2.05mm. Allocating thickness≤2.1mm,
diameter≤6.1mm, film0..0.2mm and axial play±0.5mm puts its closest face atX304.3:
exactly the retaining-guard plane. Native screening finds a coplanar surface;
this has no positive clearance and is rejected. These allocations are design
requirements, not supplier-certified tolerances.

## Deeper pocket candidate

`deeper_pocket/parts.scad` deepens only the existing pocket floor by0.2mm toX307.3.
The exterior, shaft bore, grub pilot and spring holes remain inherited unchanged.
Nominal magnet is nowX305.2..307.2; the allocated receiving envelope is
X304.5..307.8. This restores0.2mm minimum allocated guard clearance and1.45mm
minimum allocated package-face gap. The latter is not a sensor-die field gap.
Remaining nominal floor thickness to the rotor disc end atX309 is1.7mm.
Native volume removal is6.020362mm³ versus6.020912mm³ expected for the48-facet
pocket extension; the small difference is native mesh coordinate precision.

Native checks pass for nominal magnet versus pocket, allocated magnet versus
stationary sensor hardware, and magnet/screw envelopes versus all configured
current controls and cooling roles. Source identities, logs and positive meshes
are preserved. Floor strength, bond strength, field/angle performance and physical
clearance still require qualification; no fabrication release is implied.

## Retaining screw

`grub_nominal` proposes a smooth M3×3 flat-end envelope alongY atX320/Z31.6.
The tip planeY83.5 is tangent to the nominalØ3 shaft; its outer endY86.5 is
recessed in theØ10 hub. Native shaft-intersection and conservative full-rotation
stationary-hardware checks pass. The rotational envelope also includes±0.5mm
axial movement. The threaded contact with the printed M3 tap pilot is intentionally
not claimed as a clearance pass. Exact nonferromagnetic supplier, tip/socket,
thread engagement, tightening torque, shaft holding torque and print durability
remain unresolved. This is a receiving envelope, not an exact threaded solid.

Run the frozen checks from the repository root:

```sh
.venv/bin/python -m hardware.cad.two_board_magnet_09.screen check
.venv/bin/python -m hardware.cad.two_board_magnet_09.deeper_pocket.screen check
.venv/bin/python -m hardware.cad.two_board_magnet_09.deeper_pocket.full_screen check
```

The first intentionally retains the failed zero-clearance baseline. Neither
candidate alters `assembly_workflow/current.json` or the printed-part selection.
