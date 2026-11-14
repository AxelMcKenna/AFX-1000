# Combined addon fit checks

`assembly.scad` checks the new display/selector carriers, sensor carrier,
revised lever/spring assembly and external fan-pod candidate together.
The [trial03 evidence](trial03/review.json) records seven strictly empty
native intersections with thirteen source bindings. It uses the corrected
selector height and the sealed spring geometry, not the superseded early
carrier trials.

Checks cover sensor versus selectors, moving lever versus selectors,
display versus selectors, all new controls versus cooling, sensor versus
the revised lid/guide, spring assembly versus the new controls/lid/guide,
and spring assembly versus cooling. The spring uses its expanded continuous
sweep. These checks complement each addon's individual board/shell checks.

This is **not a complete installed-fit release or a new print package**.
Panel LEDs, complete cable routes, the populated sensor PCB, later cooling
lead/screen-retention changes and actual physical receiving still require
integration. Operating thermal/electrical behavior remains unqualified.
The initial cooling alternative increases overall width to 359 mm including
modeled bolt heads; the original r6 package remains unchanged.

Regenerate with a fresh output directory:

```sh
.venv/bin/python -m hardware.cad.two_board_integrated_07.check next-review
```

The runner uses the already-authorized pinned isolated Linux OpenSCAD image.
It rejects source changes during a run. Trial02's geometric intersections
were empty but its final evidence was rejected because selector source changed
during checking; trial03 supersedes it. Any later source change requires a
new combined check. No host CAD application is used.
