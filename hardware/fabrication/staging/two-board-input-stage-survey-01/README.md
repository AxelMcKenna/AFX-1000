# Input source-stage placement screen

This is a **geometric candidate only**. The selected PCB remains
[TBP27](../two-board-power-input-controls-native-02/README.md); no candidate
footprint moves or routes have been applied to it.

| Part | Candidate front position, mm | Angle |
| --- | --- | --- |
| Q101 blocking FET | 190.3, 114.8 | 90° |
| Q102 pulldown FET | 191.2, 120.4 | 180° |
| C103 bulk output capacitor | 218.5, 121.0 | 0° |
| G_NT1 return net tie | 198.7, 132.2 | 0° |
| C104 local output ceramic | 202.4, 122.4 | 0° |

The [source-bound screen](survey.json) preserves values, packages, sides and
pin/net assignments. All numbered pads being moved are currently isolated.
Courtyard/body, enclosure-context, height, mounting reserves, both-side copper,
drill spacing and C103's opposite-face lead reserves pass. Existing zone
outlines are avoided. Minimum moved-pad distance to another drill edge is
0.700 mm. G_NT1 is bare PCB copper, with no fitted component height.

Straight pad-center distances are 3.518 mm for Q102 drain to Q101 gate,
2.314 mm for its source return, 2.778 mm for the DRV connection, 8.226 mm
for Q101 drain to U101 IN, 2.718 mm for C104 to OUT and 20.039 mm for C103
to OUT. These are geometry measurements, not routed lengths or inductance
limits. Compare FET orientations and actual route/plane feasibility before
accepting the 8 mm force path. Review both output and return paths to the
remote bulk capacitor; the local ceramic does not by itself prove transient
performance. C101 still needs a close IN_SYS bypass arrangement.

The [manufacturer layout guidance](https://www.ti.com/lit/ds/symlink/tps2663.pdf)
requires short blocking-FET/pulldown connections, nearby bypass and support
parts, and power paths sized for at least twice full load. Actual stack,
copper capacity, protection thresholds, component tolerances, startup and
thermal behavior remain to be resolved. No new board has passed native
checks, and no fabrication readiness or complete installed fit is claimed.
