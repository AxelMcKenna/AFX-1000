# Selected-R1 E19 finite-PDN diagnostic

This new coarse extraction uses sealed source `dc559bd9…` and actual filled copper `90526f68…`. All pad/hole coordinates, quiet-filter references and copper fills are re-read after the same-value WSLT2512 manufacturer-land and local Seed-force repair. No prior E19 matrix, PDN, mechanical or qualification result is inherited. Nine immutable source inputs are recorded in `capture.json`; the raw native pad polygon export is `generated/pads.json`.

Source and return enter **J13.1/J13.2 F.Cu**, representing above-board solder entry. The source process assumption distributes current uniformly across the actual finite F-face annulus. It does not assert a measured solder/contact current distribution. Loads use R1.1 (Seed), J11.2 (LED), J14.1 (bypass) and J15.1 (monitor), also on F.Cu. J1 is unfitted service and is not driven. Actual pad polygons use saved absolute angles; all270 native pad/via drill voids, including unnetted H9, are present. Pads, sheets, annuli and plated cylindrical walls have finite conductivity, without equipotential shortcuts or artificial links.

The **unaccepted S1 scenario** uses four70 µm finished copper layers,25 µm plated walls,1.6 mm board, layer centroids0.035/0.285/1.315/1.565 mm, and dielectric0.18/0.96/0.18 mm. Sheet/barrel rho20 are1.724×10⁻⁵/2×10⁻⁵ Ω·mm, with α0.00393/°C. Uniform100°C is a diagnostic condition, not a demonstrated hot operating bound. No fabricator, microsection, minimum copper/wall, current/ampacity, material or process acceptance follows. A real selected stack remains required.

The actual six-vertex outline bounds are native `[100,100..264.5,165]`; the ear is not clipped. The single full-board extraction uses0.2 mm cells and lattice offset(0.025,0.025) mm. No spatial refinement or rigorous discretization bound is claimed.

| Network | Raster nodes | Finite matching barrels | Maximum wall-attachment displacement |
|---|---:|---:|---:|
|5V_DIG|335,870|12|0.189 mm|
|SEED_VIN|1,441|6|0.189 mm|
|AGND|228,723|58|0.316 mm|

All23 AGND drive ports and33 measurements resolve in the source component; KCL residuals are≤3.51×10⁻¹⁰ A and reciprocity is checked. Two5V and33AGND unexcited raster nodes float. No port is relocated or linked to hide them. Nearest-wall attachments, finite cell size and raster fragments are explicit numerical limitations.

Known positive current is **1.984 A** = Seed1 + LED0.764 + bypass0.140 + monitor0.080. Input design allocation remains2.4 A; **0.416 A has no installed endpoint**. The nested0.075 A3V3 exports are subtracted from Seed's local return, leaving0.925 A there, rather than added a second time to the positive input. Conditional child returns are converter0.035 A via J5/J6, controls0.020 A via J2/J4, and monitor0.020 A via J15 or source reference. Seed20/40 and LED1/8 sharing retain independent extremes. Actual outward AGND ports and quiet C11..C20 ground electrodes are preserved in the full transfer matrix.

The32 known-load corners are conditional direct-return fixtures, not a bound on actual remote common grounds, circulating currents or arbitrary load sharing. Two further32-corner fixtures place the unassigned0.416 A at J14 or J15 for diagnostics only. They do not change target-board0.140/0.080 A requirements or implement the missing reserve endpoint. The child current returned at source reference cancels in-plane excitation but remains part of external wire KCL.

| Known1.984 A fixture,100°C S1 | Local copper-loop drop |
|---|---:|
|Seed, excluding R1 resistance|21.519–21.883 mV|
|LED|6.055–6.192 mV|
|J14 bypass|1.360–1.372 mV|
|J15 monitor|0.994–1.008 mV|

These are fixture intervals, without complete material, mesh or process uncertainty. The actual0.47 Ω R1 adds0.4747 V and0.4747 W at1 A under assumed+1% initial tolerance; its selected MPN/full-temperature resistance/derating, actual Seed load and assembled thermal behavior remain unaccepted.20°C values scale algebraically by1/(1+0.00393×80) only for this same uniform model; that is not a second physical temperature solve or spatial refinement.

`generated/coarse.json` contains the fresh matrices,96 named corners, signed quiet-reference offsets and explicit omissions. Actual P03/E28 feedback offsets, both return bars, wire joints/harnesses,3V3 positive paths and remote return loops are not embedded. Bypass/monitor target native PCBs are still missing. Dynamic impedance/effective capacitance/stability, signal coupling, noise, startup, ampacity, thermal and fabrication qualification remain false. No endpoint-voltage or complete-system headroom pass is derived from the old lumped model.

Three tests reject five false-release/current/source mutations and independently check a tiny finite-annulus control against wall resistance and temperature scaling. The equation control is not another full-board extraction. Further large computation is gated on stable mechanically checked geometry and an agreed uncertainty/complete-network contract.

The Seed branch is still1A. Five actual new Seed_vin barrels and eight0.75mm force segments are extracted, rather than crediting two-endpoint equal sharing. R1 resistance itself remains excluded from this copper network. Its selected part/derating/thermal/pulse obligations are in the separate Seed study. The moved Seed force load also changes5V transfer coefficients at LED; the difference is a new conditional result, not inherited endpoint headroom. `generated/updated-endpoint-intercept.json` recombines this new matrix with the frozen source/resistor assumptions while preserving all unbounded signed/socket/remote terms.
