# Right ADC reference divider

A_R124 sits on the rear beside the right channel's reference filter. A 6.10 mm rear trace connects its 100 kΩ divider leg to A_C120. The gain-request signal passes underneath on In5.Cu between two existing vias. Grounded In6.Cu copper separates the routes and supports both traces. The nearest modeled body is A_R615, with 0.37 mm clearance. The codec land pattern, loaded reference noise and installed fit still require verification.

KiCad reports 80 open connections and zero copper-rule violations. The ground and connectivity checks include a fresh copper refill.

[Placement and clearances](component-placement.json) · [Ground return and routes](reference-review.json) · [Connectivity](native-review.json) · [DRC](drc.json) · [ERC](erc.json)
