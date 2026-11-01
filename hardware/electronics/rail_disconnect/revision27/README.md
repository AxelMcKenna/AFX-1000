# E27 disconnect qualification audit and routing candidate

E27 is a separate development candidate, preserving E26, E25 and A11. It retains the 164-part pin/value circuit, all component/pad positions, outline, mounts and bulk-capacitor poses. It adds 925 trace segments and 22 conventional vias over E26: **8,860 segments and 518 vias**. Native checking reports **8 open connections, 21 DRC warnings and zero parity issues**, compared with E26's 21 opens and 30 warnings. The remaining warnings are 20 dangling tracks and one copper sliver. The strict checker fails; this is not a fabrication or full qualification pass.

The repaired main header paths include N12_SRC and N19. Missing OV, reference, allow and MCAP branches remain critical: they can prevent or defeat the power interlock. Do not interpret the smaller open count as a safe power-up release. Every physical, copper-loss, thermal, startup, fabrication and build-ready flag remains false.

## What was actually checked and changed

`native_graph.py` exports connected-component anchors from KiCad's actual connectivity engine and freshly filled board. The bounded repair uses those anchors, rather than assuming the reported nearest airwire endpoints are usable escape points. All additions are ordinary traces/vias; no jumper component or ignored DRC rule closes a net. `reviewed-additions.json` and `replay.py` reconstruct the editable PCB byte-for-byte from frozen E26 plus the exact added copper objects.

Some new traces use In1.Cu, cutting clearances into its AGND pour. In4.Cu remains the other ground plane. This changes return-plane usage and has **not** been qualified for reference impedance, noise or EMI. No component moves or new mechanical clearance claims are made. The proposed P02 strap/stud interfaces are still absent.

A trial that allowed signal routes to cut power pours introduced new power-net opens; that trial was rejected. Short experiment records remain under `generated/experiments/`. The selected board preserves the power-pour reservations, uses the additional inner-layer escapes and retains every actual native finding.

## Actual filled-copper diagnostic

`copper.py` builds a finite-volume resistor network from native **filled polygons**, actual traces and lands, and finite cylindrical plated barrels. It does not replace fills with ideal ribbon rectangles. Assumed process values are 70 µm finished copper, 25 µm plating and 85 °C copper. The PCB has **no specified dielectric stackup**; equal layer spacing is an explicit placeholder for the barrel calculation.

| Positive path, excluding MOSFET channels | 0.20 mm grid | 0.10 mm grid | P02 allocation |
| --- | ---: | ---: | ---: |
| Analog source + common + output | 3.169 mΩ | 3.140 mΩ | ≤3.000 mΩ |
| Digital source + common + output | 1.055 mΩ | 1.017 mΩ | ≤3.000 mΩ |

The analog diagnostic exceeds the allocation at both resolutions. This is a model concern requiring layout/process refinement and a bounded extraction, not an independently certified resistance failure. Rounded lands are rectangularized, cell-center discretization is approximate, annuli/contact regions are idealized, and parallel FET terminal groups are equipotential electrodes. The digital result therefore **does not bound unequal or diagonal switch current sharing**.

The header-return diagnostic uses 0.40/0.20 mm grids. Its finer values are approximately 0.632 mΩ J1→J3 analog return, 0.275 mΩ J2→J4 digital return, and 0.814 mΩ between the protected analog/digital ground headers. These are two-terminal pair resistances under the same approximations, **not multiport transfer impedances or the full P02 strap/contact paths**. No unimplemented stud region is treated as a real electrical terminal. Real four-wire, temperature and current-sharing measurements remain required.

## Manufacturer findings

The [Skyworks Si8751 datasheet](https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf) gives the reviewed timing conditions at a 100 pF gate load. The existing TT=10 kΩ circuit is checked against its static gate-voltage/impedance entries; those values do not bound the actual switch waveform. The [TI CSD18510Q5B table](https://www.ti.com/lit/ds/symlink/csd18510q5b.pdf) gives up to 153 nC at its stated 10 V gate / 20 V drain / 32 A test point. Four digital FETs give a 612 nC comparison, 612 times the 100 pF-at-10 V test charge. That comparison is not an actual application gate-charge measurement or a scaled timing guarantee. The [CSD18540Q5B](https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf) has its own stated test conditions and SOA.

All 14 FET footprints have generic **0.70 × 0.70 mm** source/gate lands. TI's CSD18510Q5B recommended pattern, section 7.2, specifies **1.100 × 0.710 mm** for those lands. The footprints are not that recommended pattern, and no alternate assembly/manufacturer approval is recorded. Pin roles match the reviewed top-view diagram, but terminal tolerances, complete compound drain shape, mask and stencil still need a coordinated land-pattern review and correction/approval. The larger TI compound drain drawing must not be compared as if it were merely the generic footprint's central exposed-pad rectangle.

The native C24 bulk is 4,700 µF ±20%. At the maximum local capacitance and 5.1 V, stored energy is 73.35 mJ; a hypothetical 1 ms linear ramp needs 28.764 A average before load or downstream capacitors. This is not a predicted waveform. The interlock has no independent current limiter, and upstream soft start does not constrain a later FET closure. Avalanche energy is not the linear SOA needed to approve that event. Measure actual VDS, ID and VGS simultaneously and assess the hot transient operating locus.

This board provides a level-controlled **overvoltage-only** interlock. It adds no undervoltage qualification or separate fault latch. Opening the switches does not establish rapid bulk discharge or isolation of every signal-pin backfeed path.

## Reproduce

```sh
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.replay --check
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.check --kicad-cli /path/to/kicad-cli
# Strict native check above intentionally fails while the reported findings remain.
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.device_review
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.copper --steps .2,.1
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.copper --returns
uv run --locked python -m unittest discover -s tests/tooling -p test_disconnect_revision27.py -v
uv run --locked python -m hardware.electronics.rail_disconnect.revision27.qualify
```

`native_graph.py` requires KiCad's supplied Python/pcbnew; the copper diagnostic requires NumPy. Tests independently check exact series/parallel networks, finite barrel resistance, missing-via disconnection, gate/energy scaling, byte-exact replay, parent-item preservation and rejection of suppressed native findings. Synthetic solver fixtures are not physical captures.

`generated/qualification.json` binds the source, native findings and diagnostic outputs without converting them into measured results. Manufacturer/fabricator approval, complete routing, a specified stackup, actual copper/contact bounds, late-closure SOA, thresholds/timing, partial-power behavior, thermal/EMI and complete-system physical measurements are still required.
