This is a **new, coarse-only PDN diagnostic** on frozen e415 source and actual filled copper `f2dbe1c7…`. It inherits no old J1-source matrix or electrical acceptance. Canonical and sealed candidates stay untouched. The later mechanical integration found a J29 service collision; this electrical snapshot remains historical until a real repaired source is re-extracted.

The source and return injections are actual **J13.1 F.Cu and J13.2 F.Cu**, representing above-board solder entry. Loads are R1.1 (Seed), J11.2 (LED), J14.1 (bypass/gain) and J15.1 (monitor), also F-face. Uniform finite annulus current injection is a declared process assumption, not a measured solder-current distribution. Native pad polygons use saved absolute orientation, including all265 actual pad/via hole voids and unnetted NPTHs such as H9. Pads, sheets, annuli and plated cylindrical walls have finite conductivity; no equipotential pad/via shortcut or artificial link is added.

**Unaccepted S1 scenario:** four finished70 µm copper layers;25 µm plated wall;1.6 mm board; layer centroids0.035/0.285/1.315/1.565 mm; dielectric0.18/0.96/0.18 mm. Sheet/barrel rho20 are1.724×10⁻⁵ /2×10⁻⁵ Ω·mm withα0.00393/°C. Uniform100 °C is a diagnostic scenario, not an established operating-temperature upper bound. No fabricator, microsection, material, stack or process acceptance follows from these values.

The actual six-vertex outline sets the native domain[100,100..264.5,165]; the old150 mm-wide domain would clip the ear and is not reused. First0.2 mm preflight at half-cell phase(0.1,0.1) correctly rejected an unresolved0.5/0.3 mm barrel at(127,115). The failed log/model are preserved under `generated/history/`. The completed diagnostic uses **0.2 mm spacing, phase(0.025,0.025)** to resolve actual annuli. This is not a fine-grid sweep or a proven discretization bound.

| Network | Raster nodes | Finite matching barrels | Maximum wall attachment displacement |
|---|---:|---:|---:|
|5V_DIG|335,985|12|0.189 mm|
|SEED_VIN|922|1|0.174 mm|
|AGND|228,826|58|0.316 mm|

All33 AGND measurements/23 drive ports resolve in the source component. KCL residuals are≤3.51×10⁻¹⁰ A, and reciprocity is checked. Two5V and33AGND unexcited raster nodes float; no load/measurement is moved or linked to disguise them. Coarse wall attachments and floating raster fragments remain numerical uncertainty. No spatial refinement is performed.

The known positive allocation is **1.984 A** = Seed1 +LED0.764 +bypass0.140 +monitor0.080. The source requirement remains2.4 A; **0.416 A reserve has no installed endpoint**. J1 stays unfitted service, not a second source. Optional linear fixtures add0.416 A at J14 or J15 only as labeled diagnostics; they neither alter target-board current requirements nor bound an arbitrary unimplemented reserve location.

The nested0.075 A3V3 exports are not added again to Seed's1 A positive input. Known local Seed return is0.925 A, while0.035 A converter /0.020 A controls /0.020 A monitor return through explicit conditional remote ports. Seed pins20/40 and LED pins1/8 retain independent extremes, not50/50 sharing. Converter return choices use actual J5/J6 grounds; controls use J2/J4; monitor uses J15 or the source-reference path. Bypass/monitor direct5V returns use the new J14.2/J15.2 ports. Full23-port transfer coefficients retain every manifest outward AGND port plus Seed pins and the new outputs for later signed-network embedding.

Those fixture placements are **not** a complete bound on real external ground loops, return sharing or circulating currents. GPIO, pot/passive, SD, bypass/LED3V3 currents and actual3V3 positive-path regulation remain unbounded terms. The0.020 A monitor child returning at the source reference cancels its in-plane excitation but does not disappear from external wire KCL. Actual source/E28/P03 feedback, bars, harnesses and destination PCBs are not embedded.

| Known1.984 A direct-return fixture,100 °C S1 | Local copper-loop drop |
|---|---:|
|Seed, before R1|21.928–22.291 mV|
|LED|8.902–9.041 mV|
|J14 bypass|1.354–1.366 mV|
|J15 monitor|1.003–1.017 mV|

These intervals cover only the declared fixture corners, not material/mesh/process/complete-system uncertainty. Seed's nominal0.47 Ω R1 adds about0.4747 V and0.4747 W at1 A under an assumed+1% initial tolerance, separately from the copper result. Full-temperature resistance, selected rating/derating, actual Seed load and assembled thermal evidence are still required. No endpoint-voltage or headroom pass is derived by inserting these numbers into the obsolete lumped model.

For the same uniform material model,20 °C values scale algebraically by1/(1+0.00393×80). That is not a second temperature solve, independent physical evidence or spatial refinement. The machine-readable packet contains the full hot matrices,96 named fixture corners, quiet-reference offsets, maximum residuals and explicit unknowns.

`capture.json` binds eight original inputs copied under `sources/`; `generated/pads.json` is the actual native export; `generated/coarse.json` is the completed diagnostic. Three tests reject five false-acceptance/current/source mutations and independently test a tiny isolated real annulus against finite-wall resistance and temperature scaling. The latter is an equation control, not another full-board solve. All physical, complete-PDN, dynamic/noise/ampacity/thermal and fabrication-release flags remain false. Further full-board refinement is gated on a stable mechanically accepted source.
