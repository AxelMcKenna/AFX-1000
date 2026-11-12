# Actual AUX operating conditions and startup path

This follow-up checks the table census against the actual 2.534165–2.655700 V conditional rail interval and −40 to 85°C common temperature screen. **39 packages have current rows whose voltage domains cover that interval; 42 have only other-voltage table points.** Even the 39 require the specified pin/load conditions before their table current becomes an application bound. The 81-package whole-board bound therefore remains unset, rather than interpolating unsupported current maxima.

`analysis.json` lists each family and the exact missing condition. The native input inventory has 369 contacts marked `input`: 13 tied to AUX, nine tied to ground, and 347 on signals. This is a native symbol classification, not a claim that every analog/passive pin is included. Signal voltage, state, transitions and loading require separate treatment. Typical Cpd or supply-current curves do not establish a maximum transient current. The earlier OPA2333 fact was corrected: its electrical-table header does **not** default all rows to 5 V; the no-load current is considered within its stated 1.8–5.5 V supply range, with its other conditions retained.

## What currently conducts

`TBP72-AUX-copper.json` is an AUX-only extraction of the frozen native TBP72 capture, with original capture SHA and extraction provenance. `routes.py` builds a same-layer positive-area contact graph, matches all 188 objects in the source group, and reproduces the nine connected IC supply pads. It ranks paths by the sum of full track length/width:

| Destination | Full-track squares proxy | Vias on selected path |
|---|---:|---:|
| E_U31 | 852.857 | 6 |
| E_U42 | 811.664 | 6 |
| E_U41 | 705.495 | 4 |
| P_U201 | 445.386 | 2 |

The minimum trace width on these source-group conductors is 0.2 mm. These figures identify actual routing paths to examine. They are **not resistance upper bounds**: pads and vias have zero cost in this graph; return impedance, conductor thickness/temperature/tolerance and branch currents remain absent. A midpoint contact is charged the whole original trace length, so even the track contribution is a path-ranking proxy. A complete distribution-drop calculation cannot cover the other 72 IC supply paths until those paths exist.

Only **11 µF nominal** currently connects to both AUX source and main ground. The complete intended 28.5 µF must not be used as an already-connected reservoir. Both figures still lack receiving/bias/aging effective-capacitance bounds.

## Supervisor and reset-buffer routing targets

`startup-route-targets.json` provides exact pad/source-group identities and nearest same-surface copper objects from TBP72. The E_U19/E_U35/E_C58/E_C78 target pads are B.Cu-only; native layer membership is authoritative. It does not establish obstacle clearance or a valid new route; filled zones are excluded from its proximity list.

- E_U19.4 is at (77, 155.4) mm and already shares its isolated AUX island with E_C58.1 at (74.5, 156.95) mm. E_U19.2 and E_C58.2 already reach main ground. Its closest existing B.Cu source-connected object is about 21.50 mm away.
- E_U35.8 at (113.55, 158.75) mm and E_C78.1 at (110.5, 161.2) mm are separate isolated AUX pads. Their nearest B.Cu source copper is approximately 8.62 mm and 6.775 mm away respectively.
- E_U35.4 already reaches main ground; E_C78.2 at (112.1, 161.2) mm does not. The pairings are consistent with the existing `revision28/aux_supervisor_fanout.py` and `revision28/reset_buffer_placement_screen.py` local component groups.

## Actual inhibit chain and the timing gap

Native nets verify this path, at the independent gate level:

**E_U19 RESET → E_U35 gate 2 buffer → E_U31 gate 2 AND (other input AUX) → E_U29 gate 1 AND (other input ALL_RAILS_ALLOW) → four 100 Ω input branches → Si8751 drivers.**

The TPS3890 timing table has **no maximum assertion-delay entry**. Its 18 µs at 3.3 V and 8 µs at 5.5 V are in the NOM column, with 5% input overdrive and CT open. They cannot qualify a maximum delay at the actual rail or small overdrive. The existing E_U19 also has a populated CT capacitor. CT controls release delay, but the listed assertion test condition still does not directly match this circuit. A precise maximum for this device and operating case requires additional manufacturer evidence or an accepted characterization bound.

The Si8751 table has a 35 µs maximum turn-off time, but the common condition is a **100 pF gate load**. The actual P19 gate path, for example, drives two CSD18540Q5B devices through 22 Ω; the 35 µs maximum cannot be transferred to that load without further evidence.

Two requirements must be distinguished: force MASTER_ENABLE low before comparator supply falls below 2.4 V; then finish FET turn-off while driver VDD remains within its ≥2.25 V operating range, or establish a documented safe unpowered-output behavior. Neither complete bound is established. TPS7A16 PG may assert below 2.4 V, and the final ALL_RAILS_ALLOW gate is AUX-powered. No independently bounded alternate AUX undervoltage inhibit has been established by the inspected evidence. The Si8751 source did not provide an independent UVLO assertion-delay guarantee that resolves this gap.

A diagnostic constant-current calculation makes the missing timing budget concrete. With all **28.5 µF nominal** hypothetically connected, **58.302212 mA mixed-condition current**, no replenishment and zero distribution drop, the existing low threshold gives approximately **1.49 µs** until 2.4 V; the proposed static resistor candidate gives **13.15 µs**. Reserving 20 mV of that candidate margin leaves **3.38 µs**. From 2.4 V to the driver’s 2.25 V minimum gives another **73.32 µs** under the same assumptions. These are neither predicted failure times nor verified hold-up times: capacitance, simultaneous load, replenishment and timing remain conditional. They show why the resistor candidate alone must not be promoted to a safe startup/shutdown design.

## Next qualification decisions

1. Complete source/return routes for the supervisor and reset chain, then the other AUX loads; bound copper and branch currents to turn geometry into a distribution-drop model.
2. Obtain a maximum TPS3890 assertion delay at the actual rail and required low overdrive, plus SENSE-current limits at its actual threshold. If that cannot meet the available charge window, change the inhibit/hold-up architecture; merely selecting the static resistor candidate does not close it.
3. Establish actual Si8751 load/turn-off and OFF-current bounds, including the two installed MOSFETs, their gate network and supply decay.
4. Obtain full operating-voltage current bounds for the 42 point-specified packages and bound the nonrail/transition states for every family. The per-family ledger identifies which primary data is absent.

Fourteen checks pass, including the nine previous census/window checks, exact operating-domain classification, actual inhibit-chain connectivity, full native source-group contact connectivity, source corruption rejection and retained-report reproduction. Self-review fixed an arithmetic reproducibility issue between Python versions by using `math.fsum`, sorted graph contact layers, and corrected the OPA2333 table condition. No board/BOM/schematic was changed in this checkpoint.
