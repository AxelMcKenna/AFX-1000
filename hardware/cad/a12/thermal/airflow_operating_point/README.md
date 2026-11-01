# AP04 operating-point comparison

The original AP02 **125 mm² base meter fails the requested 1.2 m³/h base flow**
in the conservative low-speed comparison. At 5300 rpm, Cd0.6 and total10 m³/h,
the two-fan curve sensitivity provides9.046 Pa. The common guard costs4.006 Pa;
the base meter alone costs11.133 Pa. This leaves **−6.093 Pa** before pin-field,
turn, outlet and other base-path losses. The failure is retained in every run.

A 200 mm² meter leaves only0.691 Pa for the unknown base losses;250 and300 mm²
leave2.256 and3.107 Pa respectively. These are design comparisons: larger meter
geometry must be implemented and checked separately. No installed flow is
established by a positive residual. Actual flow split depends on both complete
branch resistances; area ratio cannot set it.

`analysis.json` contains135 fixed-flow parallel-branch comparisons. Common fan-guard loss is
counted once. Interior and base losses are evaluated as parallel branches, not
added as serial restrictions. It also shows the hypothetical split at fixed
total10 m³/h when all unmodeled losses are zero. That split is a diagnostic only.

The enclosing NF03C/FH02 heat provision is37.405706 W, with1.2× heat used for the
energy checks. This adopts FH02's explicit receiving proposal to increase DIG
capacity from2.40 to2.42 A; source-current, voltage, connector, startup and PDN
acceptance of that increase remain open. The0.120 W capacity change is included
once. Fan and health loads partition that capacity and are not added a second
time, nor is normal-feed loss added again to the enclosing4 A feed partition.
At40°C ambient,101325 Pa and58°C bulk
interior-air ceiling, the8.8/1.2 m³/h target covers the necessary energy transport
both with no base heat credit and with AP01's hypothetical four-land heat split.
The80000 Pa sensitivity does not pass that same target. Neither comparison
proves local component or accessible-surface temperatures.

The actual floor opening is2563.128 mm². The Trill PCB projects over335.266 mm²,
leaving2227.862 mm² uncovered in straight projection. The17.2 mm gap permits
lateral turns, so this projection is only a second loss sensitivity, not a
governing throat or guaranteed effective area. New PCB placement may change the
loss again. The original AP03 coupled-flow geometry omits the NF/FPC bodies.
A separate fixed-flow sensitivity now uses sealed FR01's actual captured
NF233/FPC84/Trill vertical projection, leaving1258.684 mm² outside their receiving
solids. This is not a governing throat, effective flow area or a flow bound;
elevated bodies allow lateral turns. FR01's optional opaque10 mm bundle box is
not actual wire and is not used here as a flow restriction. The changing
NF265/E28 boards and complete wiring still need a new assembly/airflow review.
Exhaust/guard areas are conservatively rounded down from the
reported native faceted geometry.

The later sealed AP03 geometry supplies an actual318.279 mm² meter and a
continuous rear-approach area comparison. Root verified all369 sealed files.
The additional receiving sensitivity leaves183.292 mm² per rear approach;
the coupled model conservatively applies this right-side value to both fans.
Seventy-five operating-point comparisons solve both branch flows and common
guard pressure against the fan curve. Hypothetical channel-loss coefficients
are varied independently; they are not measured or guaranteed bounds. At
5300 rpm and equal K values of0/4/8/16, modeled interior flow is respectively
9.510/8.737/8.165/7.372 m³/h. The largest-loss case fails the necessary energy
comparison, so the larger opening is not treated as an automatic cooling pass.
Actual per-fan imbalance, leakage and all loss coefficients still need evidence.

The5300 rpm comparison is below a conditional5352 rpm software acceptance floor
derived from the revised FH01's680-tick maximum, a complete±0.1% clock requirement
and±20-tick complete period-measurement requirement. The adapter now runs its
core at4MHz while retaining125kHz engine timestamps. Those timing requirements and the transfer of catalogue
fan pressure to installed low-speed operation remain unverified. No guaranteed
hot fan curve, measured Cd, leak rate, channel loss, flow split or thermal pass
is claimed.

Nineteen inputs are captured under`sources/` with original paths and hashes in
`sources/manifest.json`. This binds the reviewed AP02 draft without editing it
or inheriting whole-unit acceptance of the later mechanical variant. The AP03
handoff/channel report and sealed FH02 analysis/handoff plus final firmware
header/adapter and FR01 projection/handoff are captured separately. NF03C, FH02 and SF01 retain
their original seals. Reproduce with:

```sh
python3 -m hardware.cad.a12.thermal.airflow_operating_point.analyze
python3 -m unittest hardware.cad.a12.thermal.airflow_operating_point.test_budget -v
```

All installed-flow, thermal qualification and fabrication-release flags remain
false. This is a pressure/energy design decision record, not a fabrication kit.
