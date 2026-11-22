# Analog and digital force-return studs

E_J7 and E_J8 each join the power ground planes through six through-vias. Each stud uses two existing vias and four new 0.60/0.30 mm vias outside its solder land. The 1.2–1.5 mm top-layer spokes avoid the central mounting hole. All twelve via sites contact the same In5 ground island as the E_J4 return barrel. The native checks verified two joins and 836 remaining open connections.

A local DC model of the E_J8 to E_J4 path through In5 gives 1.261 mΩ at 20 °C with 35 µm copper. With 18 µm copper at 85 °C it gives 2.767 mΩ, or 4.98 mV at the 1.801 A digital load allocation. Both results use the 0.075 mm mesh. Parallel planes, solder joints, the hardware contact and the harness are outside this model. Full-path resistance, solder processing and stud contact resistance still require qualification. [Resistance model](return-resistance.json)

[Spoke geometry](layout.json) · [Plane contacts](plane-review.json) · [Connectivity](connectivity.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
