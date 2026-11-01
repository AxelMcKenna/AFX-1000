# Installed cooling requirement for the larger housing

The enlarged, source-loaded metal-chassis scenario needs substantially more
underside heat transfer than the earlier assumed h2/h3 cases. With 42.5179 W
(1.2 × the retained heat provision), the old hot-cluster placement, half effective
top-fin convection and 0.2 + 0.2 K/W joint resistance, the calculated requirements
are:

| Maximum modeled base temperature | Failing uniform bottom h | Passing uniform bottom h |
| --- | ---: | ---: |
| 65 °C | 9.33667 W/m²K | 9.34375 W/m²K |
| 60 °C | 14.70337 W/m²K | 14.71045 W/m²K |

These are numerical brackets under declared assumptions, **not installed
heat-transfer guarantees or qualified thermal margins**. The 0.00708 W/m²K
bracket width measures the bounded numerical search, not physical uncertainty.
The passing 65 °C endpoint is only 0.00688 °C below its screen and supplies no
additional model or manufacturing margin.

The calculation retains the sealed [CH20 model](../coupled_housing20/README.md):
334 × 188.4 × 6.2 mm base, extended pin field, conducting cut walls, actual
apertured lid/seat projection and original top fins. Heat sources stay at the
captured locations, 40 °C ambient, k140 W/mK, emissivity 0.8 and the original
boundary assumptions. Each coefficient applies uniformly to the model's
declared effective underside area. It cannot be converted to fan CFM without
an actual duct, pressure/flow distribution, obstructions and installed testing.

Twenty-four solved coefficients cover fixed endpoint/bisection evaluations
within h3–32. At every tested increase in h the peak decreases; every solve
converges and conserves heat, with maximum global residual below 0.000001 W.
The complete solver reports, interface heat flows, source projections and
source hashes are in `generated/analysis.json`. No base temperature is imposed.
The spatial mesh remains the coarse 67 × 38 base grid; this is not a refinement
or model-uncertainty bound.

Real board/package/TIM paths, internal air and replacement metal construction
remain unresolved. The existing PTV09 potentiometer family has a +50 °C
operating limit, so neither base-temperature screen qualifies panel controls.
The 20% heat stress is a planning test, not a measured load upper bound. No fan,
new material, manufactured part or physical thermal result is approved here.

Reproduce after verifying the parent seal:

```sh
PYTHONPATH=/path/to/shapely:. /path/to/scientific-python \
  -m hardware.cad.a12.thermal.installed_cooling_h20.analyze
```

The parent source is read without modification. `handoff.json` binds the source
and result bytes. Thermal qualification and fabrication release remain false.
