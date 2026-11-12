# Formed scene and selector ground branch

This receiving candidate adds13 wires on D_J2002 pin16:10scene buttons, one
three-way splice, and the two selector commons. Together with the frozen r14
left branch, `ground-contract.json` binds **29buttons,2selector commons,32wires,
one splice and two independent externally wired trees**. Every external
terminal has one wire. Native netlist lookup independently confirms both used
header contacts are LINK_AGND. The unused ground cavities are D_J2001 pins15/16
and D_J2003 pin1; D_J2003's signal wiring still needs its unselected mating part.

The exact scene order and incoming/outgoing3/4 assignments are in
`right-routes.json`; the complete drawing amendment contract is
`ground-contract.json`. Firmware/input signal assignments are unchanged.

The main feed retains the fully screened r13 source escape, then descends and
turns around the front of the scene controls. The scene9-to-scene4 link rises to
Z34 across the sensor-cable region before descending ahead of the button holder.
The ground splice moves from r12's[310,42,29.5] to **[293,32,29.5]**, axisX,
25mm long by6.2mm maximum diameter. These are project receiving limits, not a
supplier-certified final crimp/heat-shrink shape. Its exact receiving wire ports
are IN[280.5,32,29.5], OUT_A[305.5,31,29.5], OUT_B[305.5,33,29.5].

Settings wiring uses a13mm-radius formed loop with a smooth height change;
release wiring uses a12mm turn and a3D S-curve. All continuous wire paths meet
the12mm centerline-radius contract derived from Alpha5853's10×OD requirement.
The settings loop is **not** qualified opening slack. Wire paths end at joint
receiving interfaces; actual stripped-tail solder transitions and connector
emergence are still unqualified.

## Verification and scope

- Independent endpoint, native-net, graph, terminal exclusivity, analytic
  height-transition curvature and sampled-radius checks pass.
- Every right/right and right/left wire pair clears, with0.8mm minimum modeled
  surface gap among those pairs. The entire ground design retains the r14
  left/left minimum of0.4mm. Nonlocal self-intersection checks also pass.
- Bounded pinned Linux native r2 source intersections are empty for exact local
  housing/holder/selector/display structures, conservative component/pot
  allocations, and all six panel mating reservations.
- Full current root assembly validation is still required for this revision.
  Use original SCAD; no current positive STL is claimed here. The source-bound
  adapter exports feed, scene links, selector wires and splice separately.

The three wire-to-splice receiving contacts are intentional only inside the
three declared radius0.62mm port spheres (0.02mm guard over the modeled wire
radius). A native positive control measures1.318893mm³ of contact; subtraction
of those three masks leaves an empty intersection. No other positive intersection is
waived. Do not retain the old r12 splice or r14 partial right-source role when
selecting the r15 replacement.

## Fixed and moving frames

Both D_J2002 mating datums are shell-fixed while plugged. All29button terminals
and both selector wire pads are lid-mounted. The splice currently has no mount;
a lid-carried support is proposed, leaving only L01 and R01 across the fixed to
moving boundary. L01 starts[238.78,51,27.04] and ends at quantize3
[130.75,19.75,31.6]; R01 starts[238.78,48.46,27.04] and ends at scene2:4
[241.75,31.25,31.6].

There is no qualified hinge or opening sequence. The existing lid is removable;
installed curves do not prove that it can be lifted or tilted while connected.
Support ownership, strain relief, a lift/tilt/unplug sequence, controlled connector
withdrawal travel, wire deformation and service allowance must be designed and
verified. Current/fault/pull acceptance and exact solder/insulation receiving
remain open. No fabrication release or cut list is issued.
