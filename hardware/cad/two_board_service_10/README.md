# Removable lid service-path correction candidate

The installed original lever fits the closed lid, but its16mm-wide crossbar
cannot pass vertically through the12mm-wide lid opening. Native checks of the
unchanged current lid/guide against the unchanged resting lever pass at7mm lift,
fail at9mm and12mm, then pass at16mm. The clear final pose does not establish a
clear removal path. Original source-bound obstruction witnesses are retained.

## Removable crossbar

`removable_handle/parts.scad` separates the original16×8×4mm crossbar from the
4×4mm lever stem. The stem retains its original top atZ55.6; the new handle has a
4.4×4.4mm socket whose roof seats there. It retains the original exterior and
installed topZ57.6. A proposed M2×6 countersunk screw enters from the accessible
handle top into an M2 tapped1.6mm pilot in the stem. Nominal threaded engagement
is4mm with6mm pilot depth. The receiving head envelope isØ4.2×1mm; exact screw
selection, printed-thread torque, handle pull strength and durability are not
qualified. No adhesive is required by this proposed removable interface.

Proposed service order: unpower; remove the accessible handle screw; lift off
the crossbar; release lid fasteners; lift the lid. Removing the crossbar clears
the lever obstruction only. Wire flex, connector unlatching/withdrawal, other
fixed parts, handling clearance and a supported open-lid position remain open.
No full-unit opening or servicing procedure is approved yet.

## Verification and limitations

The nominal handle/body check produces only the intended seating plane atZ55.6,
with native bounding-box error below0.000002mm and approximatelyzero volume.
The non-seat clearance check excludes only the4.02×4.02×0.02mm slab centred on
that interface; it passes. It does not waive other body/handle collisions.

The full-lid Minkowski job exceeded the60-second runtime bound and was stopped.
Its evidence is retained and it was not retried. The replacement partitions the
lid/guide toX300..335,Y65..110, which strictly contains the complete measured
lever-body XY bounds. A vertical translation cannot bring excluded XY regions
into that body. The local geometry is swept continuously over0..16mm, with a
0.001mm radial expansion, and clears the revised body. This is not merely a
sampled-pose check. The handle's8mm withdrawal sweep also clears the lid/guide.
It has not been checked against every other part or wire.

All relevant positive operands passed the native mesh checks. Exact source
identities, local-scope proof, seating witness, meshes and native logs are
retained. The frozen original lever and active assembly selection are unchanged;
this is an unpromoted service-design candidate, not a fabrication release.

Run the corrected checks from the repository root:

```sh
.venv/bin/python -m hardware.cad.two_board_service_10.removable_handle.local_screen check
```

The original `screen` retains the sampled failed baseline; the first full-sweep
candidate retains its runtime failure. Do not describe those jobs as passing.
Candidate manifests include alternatives and are for checks, not a combined
installed-scene export.
