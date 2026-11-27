# Fan harness geometric checkpoint

`fan_harness.scad` adds `tbh06_harness()` without changing the frozen r7 cooling source. It models two internal bundle envelopes and individual terminal-entry wire envelopes. It is a geometric routing candidate, not an assembly release: internal supports, exact terminal bend transitions, external bay routing and service slack remain to be completed.

The two identical fans use these deliberately assigned channels:

| Physical pod | Feedthrough interior centre (mm) | Board mate | Bundle centreline length inside shell |
|---|---|---|---:|
| Rear, Y145 | (3,175.25,15) | F_J202, FAN_L | 64.795 mm |
| Front, Y45 | (3,75.25,15) | F_J203, FAN_R | 120.248 mm |

The words LEFT/RIGHT identify circuit channels; both physical fans occupy the left housing wall. Pin 1 is black/PWR_AGND, pin 2 red/channel switched 5V, pin 3 yellow/channel tach. Each mate is XHP-3 with the source-selected legacy SXH-001T-P0.6 contacts. Actual pad coordinates/nets are preserved in `interface-manifest.json`. Verify housing cavity numbering and continuity; never infer connector orientation from wire colours.

The [JST XH specification](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf) gives **9.8 mm assembled board height**. With board top Z9.5, housing top is Z19.3. Z22.3 in the route files is a wire breakout datum 3 mm above the housing, not the housing height. Three individual terminal envelopes extend from that datum to Z19.3 at actual pad X positions. Their final 10% spread is only an allocated envelope, with nominal 2 mm wire diameter; it does not establish a manufacturable bend shape or crimp strain relief. The nominal fan lead receiving range for the exact selected legacy contact is insulation OD 0.9–1.9 mm.

## Bounds and evidence

`route_pair.py` searches both bundles together. The earlier individual searches are preserved as rejected search evidence: their paths were individually clear but collided with each other. Only `route-pair-search.json` feeds this CAD.

`prove_routes.py` checks the quintic Bezier centrelines with derivative-control convex-hull bounds. Between samples, distance can decrease by at most maximum speed times half the sample interval. Curvature uses corresponding speed, acceleration and jerk bounds; this is a continuous conservative bound, not just a minimum of sampled radii. The modeled bundle radius is 2.5 mm. Results in `route-continuous-proof.json`:

| Quantity | Rear/F_J202 | Front/F_J203 |
|---|---:|---:|
| Component-box clearance lower bound | 0.382 mm | 0.332 mm |
| Centreline bend-radius lower bound | 10.139 mm | 10.148 mm |
| Maximum centreline Z | 39.300 mm | 35.282 mm |

Mutual bundle clearance is at least 0.485 mm. Bend radius ≥9.5 mm is a project design allocation, not a manufacturer qualification of the actual fan cable. The receiving bundle must fit Ø5 mm. Native CAD intentionally inflates the bundle radius to 2.56 mm to cover polygonal tessellation and chord error. Intentional insertion into each route's own connector is excluded from its obstacle check; every other connector remains an obstacle. This is not evidence of mating tolerances inside the connector.

Native receipts bind the exact SCAD and included housing sources. The checks cover both route/terminal envelopes against captured components, tails, controls and mounting posts, mutual separation, shell and PCB outlines. Root integration must additionally check the latest carriers, sensor, spring, lid guide and all other harnesses.

The SUNON source specifies 300±10 mm factory leads, but these internal lengths are **not cut lengths**. Motor-to-slot distance, relaxed motor lead section, retained bay routing, terminal strip/crimp consumption and service allowance must be added and verified against the minimum factory length. Do not cut based on this document.

## Remaining interface work

`interface_manifest.py` classifies all 78 captured connector/probe/terminal entries independently. Test probes are not counted as operating cables. JST XH families have explicit compatible housing/contact candidates; direct-solder proposals and M3 force terminals remain individually identified. Generic headers still require exact male-header identification, remote endpoints and a mating/cable choice. The NF module's unselected physical interfaces remain explicit; this does not invalidate the two source-selected fan interfaces.

No actual I2C route length or cable capacitance is claimed here. A 200 mm allowance discussed for electrical analysis is a hypothetical design bound until routed, measured and tied to an exact cable.
