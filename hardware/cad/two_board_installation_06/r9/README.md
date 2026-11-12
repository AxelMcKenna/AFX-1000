# TBH06 r9 — routed external fan lead bay

This separate revision preserves r7/r8 and keeps the overall modeled envelope **363.6 ×192.4 ×45.6 mm**, excluding feet and external plugs. It lowers the local retention bridge, deepens the bay floor pocket, moves the lower cover fastener, and provides a continuous external bundle route to the unchanged feedthrough. It includes the r8 internal routing eyes and individual terminal transitions.

Use `tbh09_installed()`, `tbh09_shell_variant()`, `tbh09_harness()` and `tbh09_fans()` from `cooling_candidate.scad` for integration. Do not combine old r7 bay caps with the changed r9 pod: the lower cap fastener moved from local(Y32.5,Z10) to(Y24.5,Z6). The upper fastener remains(Y32.5,Z42). Both remain M2×12 with the existing receiving head/nut allocations.

## What changed

The old bridge intercepted a direct descending lead path. The new bridge occupies Z9..11, below the wire route. Its two strap slots moved along X to clear the curved bundle; the widened local cavity also clears the full strap, not merely the bridge slots. The outer bay starts at Z3.5, its cavity floor at Z5, retaining a 1.5 mm floor. These changes fit within the existing main pod height and depth.

The external bundle centreline has two tangent circular turns of **10 mm radius**, then a straight run through the port. The nominal bundle radius is 2.5 mm. Its path from project datum `(-11,Yc+22.85,34.656086)` to interior port `(3,Yc+30.25,15)` is **32.7857 mm**. `external-path.json` preserves all coordinates. Native geometry uses radius2.57 mm; `verify.py` proves this encloses the exact arcs after chord and sphere-faceting allowance. Radius10 applies to the bundle centreline, not an independently verified minimum for every strand inside that bundle.

The loose T18R strap envelope is2.5×1.1 mm, with its top at Z19.3..20.4. A separate **5.5×5.5×3.4 mm maximum tie-head receiving box** is reserved below the bridge. That box is a project receiving constraint, not a dimension attributed to HellermannTyton. Confirm the actual selected T18R lot fits it, strap thickness≤1.2 mm, and head orientation allows threading. The strap may then be tightened around the insulated bundle; the pre-tightening envelope is not a model of the final compressed shape. Native capture and clearance tests do not establish pull strength or insulation abrasion life.

## Factory lead receiving and trimming

The official [SUNON drawing](https://www.sunon.com/PROSEARCH_FILES/%28D04114160G-02%29-1.pdf) specifies the fan lead type, colours and300±10 mm length. It does **not** dimension the actual lead-emergence position along the fan depth or its exact corner offset. Consequently the short factory-exit-to-project-datum transition is not proved by this CAD. Inspect a received fan in the selected orientation and verify a relaxed, abrasion-free transition to the first datum without loading the motor termination. If this cannot be formed inside the slot/bay, reject the fit and revise the bay; do not move the wire through the impeller or force a kink to match the nominal path.

Assembly and cut method:

1. Receive the exact fan part and verify colours, insulation OD0.9..1.9 mm, lead length and local exit transition. Keep all factory leads full-length initially. The source's5±0.3 mm factory strip is not automatically the correct JST contact preparation; trim that exposed end away during final termination.
2. With the cover removed, pass the uncrimped leads through the bay route and bushing. Route the rear fan to F_J202 and front fan to F_J203 through the three closed r8 eyes. Confirm lid/guide clearance using the installed supports and complete wire shape.
3. Position the mating XHP-3 housing and use the established qualified JST crimp preparation setup as the termination reference. Mark each wire separately after routing; remove excess at the connector end and prepare/terminate according to the exact legacy SXH-001T-P0.6 tooling instructions. Do not crimp multiple conductors in one contact. A universal precut length is not authorized from this model because the factory exit transition and contact preparation allowance are not dimensioned here.
4. Map pin1 black/ground, pin2 red/switched5V, pin3 yellow/tach. Confirm housing numbering, continuity, no exposed conductor outside the terminal, and terminal retention. Fit the bay tie only after the path is settled, leaving the motor-end section relaxed.
5. Verify the connector can be unplugged with the lid removed by releasing the relevant support bracket if needed; do not pull wires to extract it. This is a service procedure, not a claim that a fixed 10 mm extraction sweep is proven. Refit the support, inspect the route, then close the cover. Physical pull/abrasion/rotation and operating tests remain necessary.

`length-budget.json` gives nominal datum-to-housing-entry paths of100.14–101.39 mm for F_J202 and155.18–157.27 mm for F_J203. These include the external path and separate terminal curves, but use the bundle centreline upstream of fanout. They are **not cut lengths or rigorous individual-wire upper bounds**. Add the measured factory transition, actual packing/formation length and qualified terminal allowance. Compare each measured requirement with the received lead before trimming. Do not leave surplus factory length coiled in unmodeled space.

## Verification and remaining release gates

Sixteen strictly empty native checks cover external bundle versus pod/cap/bushing/fan/tie; whole strap and head receiving box versus pod/hardware; changed parts versus captured components/controls/fans; fan seats and bushing seating. One positive shifted-tie test proves geometric capture. Three closed exports cover pod, cap and full harness. Earlier versions are preserved in `native-first/` and `native-second/`; a0.0867 mm tie-to-bundle contact was corrected before acceptance.

The original shell/lid/pod contact classification and latest-carrier cross-fit remain root integration evidence. Physical receiving of the undimensioned fan exit, tie head, crimp preparation, printed clearances and clamp torque remains open. Airflow/pressure, whole-unit heat and thermal qualification remain open. This revision does not close those gates by passing nominal CAD tests.
