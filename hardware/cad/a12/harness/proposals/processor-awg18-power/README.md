# Private E19 power-distribution repair and finite-network diagnostics

This workspace preserves the actual closed `52dcb485` direct-solder receiver proposal and canonical E19. Its initial power candidate adds only three 5V fills on F/In2/B inside native [111.5,102.5]..[149.5,124.5]. In1 AGND and every original part, filter trace, pad, pose and pin map remain unchanged. The separate `stitch_trial/` adds six real 0.60/0.30 mm plated through-vias to connect overlapping positive fills. Both candidates pass fresh full native ERC/DRC/parity/connectivity with zero findings; this is electrical geometry closure, not current or supply qualification.

`review.py` and `verify_stitch.py` independently compare exact original board objects and all 76 component pin maps. `generated/filled.kicad_pcb` in each workspace is the actual native saved refill. `native_pads.py` exports actual KiCad copper polygons for exactly FOUR layers with an inside 1 µm curve approximation; saved pad angles are handled by native KiCad rather than added twice.

`mesh.py` rasterizes actual filled polygons, tracks, native pad shapes and drill holes. Plated barrels have finite longitudinal and circumferential sector conductance. Pads and within-layer annuli are not shorted into ideal nodes. Current is distributed over the actual source B-face solder land and F-face load lands; source/load face selection is explicit. Uniform contact injection and nearest-cell wall attachment are approximations, and grid differences are reported. A coarse 0.2 mm grid fails to resolve an actual ground annulus and is rejected. There are no artificial copper bridges, E28 six-layer defaults or area-only resistance claims.

The preserved load target is Seed input 1 A plus LED 5V 0.764 A, simultaneously. R1 is the actual 0.47 Ω series filter to U1.39 and does not carry the LED branch. Its initial +1% drop/dissipation at 1 A is 0.4747 V / 0.4747 W; exact hot TCR, derating and noise remain unaccepted. Older E19 0.5 A and legacy 0.6 A screens do not establish the 1 A reserve. The converter/controls/monitor 3V3 allocations total 0.075 A and remain nested inside Seed input. They are subtracted from local Seed return; remote return sharing stays symbolic rather than being added as a second input load or treated as zero. GPIO/LED3V3/SD/sensor/passive and actual source-current bounds remain incomplete.

`analyze.py` retains full independent Seed20/40 and LED1/8 return-sharing corners for the local DC portion and exports additional remote-return unit columns. `full_ground.py` provides all actual manifest AGND connector ports for later external-network embedding. `subrails.py` extracts actual V3V3_IO and V3V3_ANALOG positive matrices, without pretending these create extra R1 input current. The missing global return solution is explicit.

The S1 engineering requirement is minimum 70 µm finished copper on all four layers and minimum 25 µm through-wall, at nominal total 1.6 mm. `construction-requirements.json` separates this requirement from unaccepted centroid/material/temperature scenarios and missing maximum/tolerance/process bounds. The old 35 µm case is a diagnostic comparison. A zero native DRC result does not fulfill this stackup requirement.

The retained LED target is [4.9,5.1] V at the downstream input/anodes, with unchanged 20 mV dynamics and 2 mV local-spread allocation. J11 is not assigned an invented independent acceptance window. The earlier retained lumped result has 7.0883 mV anode headroom but already allocates 0.5 mΩ to the E19 board escape in EACH DIG-PROCESSOR lead. Actual E19 matrices must replace that allowance inside the complete source/ground/LED-harness network, not be double-counted on top or simply subtracted from the old minimum as a new proof.

No physical measurements, complete PDN, accepted ampacity/material/stackup/contact process, noise, dynamic, full-system endpoint or fabrication release is claimed. P03 AUX effective-capacitance/stability, bipolar startup and all earlier physical holds remain open.

## Results and current scope

The finite local LED positive-plus-return drop includes 0.925 A at Seed return and 0.764 A at LED return, independently sweeping both possible Seed and LED ground pins. It excludes the unresolved remote 0.075 A redistribution and the complete external ground loops.

| Actual copper candidate / scenario | 20 °C local LED drop | 100 °C local LED drop |
|---|---:|---:|
| Original receiver, 35 µm, 0.1 mm grid | 56.169–56.509 mV | 73.828–74.275 mV |
| Three fills, 35 µm, 0.1 mm grid | 10.044–10.385 mV | 13.202–13.650 mV |
| Six stitches, 35 µm, 0.1 mm grid | 6.101–6.430 mV | 8.019–8.451 mV |
| Six stitches, S1 70 µm, 0.075 mm grid | 3.345–3.491 mV | 4.397–4.589 mV |

For S1, refining 0.1→0.075 mm changes the largest hot local LED drop by −0.04068 mV (0.887%). This is a diagnostic grid difference, not a certified uncertainty bound. The refined hot Seed copper path before the R1 resistor drops 32.943–33.342 mV; R1's initial-only 474.7 mV allowance is additional. The largest hot quiet front-filter ground offset relative to either Seed ground is 0.76344 mV. These are real DC-return diagnostics, not accepted ADC/noise performance.

`generated/summary.json` binds twenty cold/hot cases and ten grid comparisons, the frozen old retained endpoint report, and all remaining gaps. `stitch_trial/generated/full-ground-cu70-grid0.1.json` contains the 21 actual manifest/Seed return ports plus ten quiet filter reads for later complete external-network embedding. All 10 full local diagnostic reports pass source/native verification. Four boundary/mutation tests pass, including rejection of an unresolved real annulus, disconnected electrodes, stale source hashes and physical-pass promotion.

The six-stitch source is `e011588d…`, with actual saved native refill `0eab7177…`. The three-fill comparison source is `930d4401…`. Both preserve the sealed receiver `52dcb485…`; no canonical PCB or frozen receiver was changed.
