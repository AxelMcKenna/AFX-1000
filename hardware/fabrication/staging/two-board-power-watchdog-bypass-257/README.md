# Fan watchdog bypass

F_C6 is the 100 nF local bypass for watchdog F_U4. It sits on the front beside the VDD pin and returns to a ground via connected to the watchdog ground. The VDD trace is 2.72 mm long and the ground trace is 4.26 mm long. The former 3.54 mm return spur was removed. All 31 fan 3.3 V pads now reach the source.

The original module places C6 next to U4 and identifies C6 as a local 100 nF front-side bypass. [Module placement](../../../qualification/boards/fan_health/composite/place.py) · [Original BOM](../../../qualification/boards/fan_health/composite_nf_branch/bom.csv)

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| V3V3 | F_C6:1 and F_U4:1 | F.Cu | 2.72 |
| PWR_AGND | F_C6:2 and F_U4:4 | F.Cu | 4.26 |

 KiCad verified every expected pad group across the board. There are 935 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
