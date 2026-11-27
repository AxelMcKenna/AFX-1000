# Conditional scene0 holder source channels

This additive candidate removes only plastic from the exact scene0 switch
holder to accommodate the fixed D_J2001:9 TAP and D_J2001:11 AUTO source exits.
The R35 obstruction proof remains unchanged. Both exits retainZ27.04, initial
+Z tangent and R12; they turn at azimuth129.6°, the holder's local−Y direction.
Neither the connector stack nor any button/PCB/terminal pose changes.

`holder.scad` delegates to the frozen housing/button modules. The source channel
is a radius0.9 mm swept receiving cut around the two source curves. After
sphere tessellation and chord error it leaves at least0.280555 mm beyond the
radius0.6 mm wire model. The generated source arcs are not complete panel wires.

## Verified local geometry

- Removed plastic:4.154886 mm³, about0.779% of original holder volume. This
  percentage is geometry bookkeeping, **not a strength metric**.
- Revised holder:closed994-triangle boundary after excluding16 zero-area
  triangles, zero bad directed edges; one connected surface component.
- The cut is disjoint from the exact switch body/plunger, nominal retaining
  clip, full key/clip motion, and a conservative source-dimensional guard for
  spring/puck/stem motion. No actual nonplastic button geometry is removed.
- Both complete original mounting posts and all four original lead bores are
  untouched. The full6×6 mm switch-seat footprint retains its upper0.5 mm layer.
  The floor below that layer is locally relieved; its original full thickness
  is **not** claimed everywhere.
- Both source wire envelopes clear the revised holder.

The local−Y channels open toward the holder edge. An orthographic review of the
exact native meshes is retained as `holder-review.png`; orange identifies the
removed plastic. This view confirms the edge relief location relative to the
mounts and four lead bores, but is not a structural simulation.

## Remaining gates

Printed strength, creep, support under pressing loads, retention and bridge
printability need qualification. A protected0.5 mm bearing layer alone does not
prove adequacy. Complete downstream wire routes, neighboring controls and full
assembly clearance are not yet checked for this revision. The source mating
stack remains conditional; full lid opening and strain relief are separate.
Other D_J2001 source cavities do not inherit this clearance.

No workflow selection, board file or frozen control source is modified. Zero
panel edges are marked complete. `scene0_relieved_holder()` and
`scene0_relieved_mechanism()` are explicit candidate modules for later paired
route/integration checks, not replacements selected automatically.

Run `.venv/bin/python -m hardware.cad.two_board_installation_06.r36_scene0_relief.verify`.
The verifier checks exact source/terminal inventory ownership, original source
hashes, every native result and mesh connectivity. Self-review specifically
separated plastic subtraction from nonplastic protection and bearing geometry
from unproven material strength.
