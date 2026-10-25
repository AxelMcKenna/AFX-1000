# A11 housing with E25 disconnect-board placement

A11 retains the 334 × 157 × 38 mm RMX-style chassis, 29 guided buttons, ten knobs, selectors, optics and release lever. It carries forward the verified A10 main-supply positions and adds the E25 164-part rail-disconnect candidate at datum (8,108.5,4.6) mm.

The new PCB has a 156 × 45.25 mm bounding box with corner reliefs for the case fasteners. Four M2 floor mounts are added. C20 and C24 avoid the front button supports. Capacitor cylinders use maximum diameter/length from the Panasonic FR-A drawing plus the stated seat/board allocations. A local opening in the guide and inner lid ledge preserves 2 mm of vent air above C24 while retaining the outer wall, lid and control positions.

Native checks cover all printable solids, full button travel and release-lever sweep, existing supply thermal/clearance allocations and a new 0.25 mm margin around disconnect components, leads, fixing heads and vent-air allocations. The report owns the result; physical fit and component height, fastener and harness allocations remain unqualified. The minimum allocated floor gap for E25 is 0.30 mm with leads trimmed to at most 1.5 mm including solder.

E25 is placed only: 365 native open connections remain. Its six-rail interlock has no routed copper, fault timing or physical protection approval. The source-harness trial also exceeds the remaining analog/digital 5 V loss budgets. Other standalone boards and full-unit integration remain unfinished. This is a mechanical review package, not a build-ready electronics release.

```sh
python3 hardware/cad/a11/build.py --openscad /path/to/openscad
python3 -m hardware.cad.a11.verify
python3 -m unittest discover -s tests -p 'a11_integration_tests.py' -v
```

The source base remains the preserved higher-headroom design; the main checkout's B1 budget/A08 edits and earlier A09/A10 review archives remain separate. See [E25](../../electronics/rail_disconnect/placement/README.md) and the [power interconnect plan](../../wiring/README.md).
