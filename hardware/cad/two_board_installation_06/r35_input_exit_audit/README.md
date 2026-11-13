# AUTO input source obstruction — fixed receiving contract

**D_J2001:11 / CONTROL_01 cannot reach its remote AUTO terminal under the current
vertical-exit Z27.04 / minimum-centerline-R12 receiving contract without crossing
scene0's plastic switch holder.** This does not prove the housing cannot be
completed: a separately verified holder relief or qualified interface change
may resolve the obstruction. Nothing selected is changed here.

The owner is exactly `switch_holder(b)` for `b[0]=="scene_0"`, installed by the
frozen `button_pose(b)`. `scene0_holder.scad` delegates to those sources; it does
not redraw the holder or substitute a broad box. Current source and button poses
are preserved. The separate +Y trial at D_J2001:9 / CONTROL_02 (TAP) also collides,
but no all-direction impossibility is claimed for TAP.

## Reachable-centerline proof

A curve starting vertically with curvature magnitude at most1/R can move
horizontally by at most `R-sqrt(R²-h²)` before its first crossing of a height
h<R. Maximum displacement occurs by immediately bending at maximum curvature
in one fixed plane. Bending to a smaller angle and then continuing straight
cannot increase that bound: its displacement is
`R*(1-cos(theta))+(h-R*sin(theta))*tan(theta)`, increasing up to
`theta=asin(h/R)`. Changing horizontal heading cannot increase horizontal norm.
The tangent cannot become horizontal or reverse vertical direction below this
plane: even maximum curvature requires a height riseR to reach horizontal.

At Z33.21–33.22, h≤6.18 mm gives a reachable disk radius1.713718 mm. The native
probe uses a circumscribed128-gon and adds0.01 mm radial guard. Its positive
solid is closed508 triangles, zero degenerate/bad edges. Subtracting the **exact
scene0 holder alone** leaves an empty result: the whole guarded disk is inside
the plastic. This blocks every centerline passing that height, even before
allowing finite wire thickness. The AUTO target is37.971898 mm away horizontally
atZ31.6, far beyond the possible displacement before crossing the tested plane,
so terminating below the plane cannot bypass the obstruction.

This result depends explicitly on vertical initial exit, sourceZ27.04 and R12.
The r10 mating stack remains a receiving condition, not controlled manufacturer
registration. The proof is not extended to arbitrary connector substitutions,
smaller bends, moved headers or changed holder geometry.

## Native evidence

- Guarded positive reachable disk and owner-only remainder: r3, closed positive
  and empty remainder.
- Earlier union/owner-only containment results remain under r1/r2 with their
  exact probe snapshots; they are not overwritten.
- +Y AUTO trial collision:2.920460 mm³, bounds[208.100235,52.015476,33.2] to
  [209.299759,54.744377,36.221901].
- +Y TAP trial collision:0.137383 mm³, bounds[205.827286,52.015476,33.2] to
  [206.759766,52.902676,34.079514].

`verify.py` binds the source contract, target identities and all native
source/result/log/mesh artifacts. No panel edge is marked complete.

The next additive candidate will assess outward local−Y channels in this
plastic, preserving switch position, mounting posts, lead locations and the R12
wire condition. The cut must be disjoint from actual switch/body/moving parts;
strength, support and retention cannot be inferred from an empty wire check.
Other D_J2001 cavity exits need their own audit; this pair is not a blanket
clearance for all16 contacts.
