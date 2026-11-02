# DC01 — combined digital/control placement

**138 electrical parts and five proposed mounting holes** are placed in a
notched **114 × 60 × 1.6 mm** four-layer allocation. Enclosure datum is
**[184,44,7] mm**; +Y points toward the performer. The front-right relief clears
the inlet PCB and the retained J2 mating reserve. The right edge stays left of
the release mechanism. Three control expanders and other small components use
the underside; top-side headers and Seed socket remain accessible after panel
removal, subject to the unfinished assembly/service sequence.

The full isolated Linux KiCad 10.0.7 review reports:

| Check | Result |
| --- | --- |
| Native geometry findings | 0 |
| Schematic parity findings | 0 |
| ERC findings | 0 |
| Ignored DRC / ERC categories | 0 / 0 |
| Unrouted connections | **466** |

This is a **placed-only PCB**. It has no tracks, vias or planes. The nominal
four-layer allocation is not an accepted stackup. No routing, return-current,
power-capacity, EMI, touch-noise or analog-input performance claim is made.

`placement-handoff.json` independently checks all actual pads against the
native schematic export and the original three circuits, the exact 6630 mm²
profile, side-specific component courtyards, 0.3 mm same-face spacing, 0.5 mm
profile allocation and proposed 7.2 mm mounting-hardware reserves. Opposite-face
parts are screened against actual THT land boxes expanded 0.5 mm for solder.
That expansion is a project receiving requirement, not an approved solder
process. Full component, mating, harness and support tolerances remain open.

Earlier trials are retained: placement-01 had 199 global-net spelling parity
warnings and five default-ignored native categories; placement-02 corrected
those but overlapped the older inlet J2 mate reserve. They are **unselected**.
This revision enlarges that relief and moves J3005 and the nearby mounting hole.

```sh
python -m hardware.fabrication.audit_digital_layout --check
python -m hardware.fabrication.assembly_layout --check
```

The [AP01 arrangement](../assembly-layout-01/README.md) screens declared digital
height allocations against the retained control/rear context. These are
conditional design limits; the full latest assembly has not passed a renewed
native fit review. No fabrication release, supplier upload or order is made.
