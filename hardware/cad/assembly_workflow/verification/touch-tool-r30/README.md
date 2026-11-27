# Touch-mount nut tool: full-assembly process screen

This candidate tests the r30 removable nut-insertion tool against all 76 other selected modeled roles. The 77-role installed selection is frozen in `previous-manifest.json`; `current.json` is not changed. The tool is a process sweep, not hardware left inside the housing.

The one excluded role is the tool's own nominal touch fastener pair. The receiving tool tip can reach Z3.55 for a nut whose tolerance-case bottom is Z3.55; nominal nut bottoms instead sit at Z3.2. Comparing those incompatible poses would create a false interference. The separate r30 nominal-tool/nominal-hardware native check remains required and verified. This exclusion does not establish real nut bearing contact or allow any external collision.

`build.py` retains the selected geometry, binds the local tool evidence and forms ten groups of at most eight external operands. Every external role occurs exactly once. Export evidence proves the access sweep is a positive closed native solid; `results.json` records all ten passing native intersection checks. The source-bound r89 board identity was used for this process screen; the subsequent r98 integration preserves all physical poses.

The assembly process needs a stable fixture with 40 mm underside access, so this is not an on-table service operation. Actual hand access, nut bearing-face/chamfer compatibility, washer registration, insertion force, tightening torque and printed retention still require qualification. Both modeled tools are swept together; this conservatively covers their individual use but does not certify a human assembly procedure.
