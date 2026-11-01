# P03 complete replacement supply — engineering candidate

P03 is a new complete supply for the standalone unit. It replaces the legacy
E14 supply and the old E23 series guard; it is not a drop-in P02 implementation.

The separate [AX03 RUN transmitter candidate](candidates/ax03-run-transmitter/README.md)
now integrates the matching low-power E28 source interface into the strict
centering successor. Its 264-part paired project has fresh zero DRC errors,
warnings, opens, ERC and parity findings with all native categories enabled.
The original outline, mounts and strict-source power copper remain intact;
five new via-in-SMD process requirements, harness, actual-band current/threshold,
PDN/thermal/fault and physical acceptance remain open. This candidate is not
promoted into canonical P03 or released for fabrication.

The original sources and immutable manufacturing archives are unchanged.
**This candidate is not released or physically qualified.** The source-bound
`generated/current-native.json` points to the latest working native diagnostic;
its scope states whether ERC and schematic parity were actually checked.
Full checks are recorded in `generated/verification.json`; compare its source hashes
before treating it as current. Earlier receipts are preserved in
`generated/history/`. An electrical interval calculation does not close an
unrouted board. The closed `42addb43` checkpoint passed fresh schematic ERC,
all-severity PCB DRC, schematic parity and native connectivity with **zero issues
and zero opens**. This closes the native routing gate only.

Two separate thermal repairs also have fresh complete native closure:
[U102 nine-EP spreading](candidates/u102-on-42add/README.md) (`138931e3`) and
[front-side U10 eight-EP reconstruction](candidates/u10-eight-ep-on-42add/README.md)
(`f94c8005`). Their exact original-copper removal ledgers, filled boards,
construction and raw native artifacts are retained in each candidate. Neither
is promoted into canonical P03. Restored control/SET/filter routes and new
foreign-net barrels alter the actual thermal and return fields, so the earlier
models cannot qualify these sources. The portable proof checks reject stale
PCB bytes, missing native artifacts and physical-pass promotion.

The separate [U10 contact-copper restoration](candidates/u10-B-transits-on-f94c/README.md)
(`1e4cb16f`) also has fresh zero ERC/DRC/parity/open counts. It moves the
quiet SET crossover to In1, retains Kelvin sensing after R37 and restores a
short front-side SHDN escape. Its exact ledger identifies four removed
dangling source barrels and six new transfer/stitch barrels. It preserves all
eight direct U10 EP barrels; actual thermal and return extraction must use its
new fills and foreign-net voids. The earlier closed `f94c8005` source fails the
declared thermal sensitivity scenario and is retained as a comparison.

The earlier U102 comparisons preserve a confirmed manufacturer-layout failure:
required local C102/C106 were on B while U102 is on F. The separate
[front-side AUX cell](candidates/aux-front-cell/README.md) (`37fd6109`) adds the
actual local VIN_IC bypass and moves local OUT/DELAY capacitance to F, with six
bounded direct F paths verified against native copper. Its complete native
ERC/DRC/parity/connectivity counts are zero. Bias/temperature/aging effective-C
minima, ESR/stability, actual thermal/return extraction, passive land/assembly
acceptance and physical qualification remain open. Earlier opposite-face
sources are retained as comparisons, not stability-approved alternatives.

The [private combined draft](candidates/aux-u10-combined/README.md) (`db83a26f`)
composes both actual closed repairs with fresh zero ERC/DRC/parity/open counts.
Its exact UUID/object ledger detects conflicting shared edits, and its saved
native refill preserves the authored merge. It retains nine U102 EP barrels
and the **two** named adjacent barrels actually present in AUX37fd; historical
claims of three adjacent additions were incorrect. The combined packet requires
new thermal, return and mechanical evaluation and is not promoted into canonical
P03. Original closed candidates and evidence remain unchanged.

The `10.5577567 W` heatmap is **supply loss only**, not total standalone heat.
Power delivered to the protected digital/analog/bipolar loads needs a separate
component-to-enclosure thermal ledger. A 60 or 65 °C base temperature remains a
scenario until full-unit measurements and uncertainty establish a bound.

The protected load targets remain 2.4 A digital and 0.251 A analog. The digital
source is a TPS543620 direct buck, avoiding the LT3083's roughly 3.5 W loss,
SET-current startup floor and load-capacitance dependence. A separate 6 V
TPS543620 preregulator supplies the ADR4550/OPA2192/LT3045 analog path. LT3045
fast SET start is disabled. Its op-amp powers from protected input before the
raw bipolar converters start. Both bucks use real TI RPY0014A lands, including
the split switch terminals, with no invented exposed pad.

The retained LT3471/LT3080/LT3090 circuits generate ±19 V and ±12 V. U8 already
uses the lower positive raw source. The negative low preregulator alone is now
nominally −14 V (R48 is 10 kΩ); historical net `RAW_N17` is retained for interface
continuity. Positive raw remains +17 V: lowering it to +14.8 V at 13.2 V input
would require duty below the LT3471's 15% typical minimum. No guaranteed
full-temperature minimum-duty or hot switch-current limit is invented from
typical curves. The LT3471 electrical table uses ambient temperature and its
guaranteed/characterized ranges must not be confused with absolute maximum
junction temperature. The project's conservative junction allocation is 85 °C.
The inherited LT3471 symbol label is corrected: pin 5 is the quiet FB2N input;
exposed pad 11 is the sole power ground. Their native ground nets are unchanged,
but the current/voltage extraction must keep these electrodes separate.

## Physical and electrical interfaces

The six-layer, 1.6 mm candidate is 160 × 45 mm with lower boss reliefs. Its A12
datum is housing (168,108,6.5) mm. The full native stack, mounting exclusions,
actual courtyards and source fingerprints are recorded in `generated/placement.json`.
The candidate requires ≥50 µm plated barrels, 0.16 mm tracks/clearance, 0.60/0.25 mm general through vias and a specific 0.55/0.20 mm monitor
via-in-pad (at least 0.175 mm nominal native annulus), filled
and capped via-in-pad construction, at least 85 µm finished copper on both outer layers and 70 µm on the four inner layers. Resin
fill is not modeled as solid copper. The exact TI RPY manufacturer package has
0.15 mm internal pad spacing; the native rule exception applies only between
pads in the same U20 or U23 footprint. This is a custom process request, not a
blanket clearance waiver. Fabricator acceptance is still required.

The U25.3 monitor via is a real 0.55 mm land / 0.20 mm finished bore. At the
actual 0.635 mm SSOP pitch and 0.40 mm adjacent-pad width it retains exactly
0.160 mm nominal copper clearance. Its native annulus is 0.175 mm; with the
required 50 µm wall its example preplate ring is 0.125 mm. The project now
explicitly requires a **0.20 mm minimum finished hole**. This is an additional
fabricator requirement; drill, etch, registration, fill/cap and tolerance approval
remain open. The 0.16 mm copper clearance was retained.

Final routing moves C300 to F(151.5,14,90°) and R302 to F(145.2,10,0°).
The saved board independently retains all eight local bulk and eight separate
HF VIN/return links and all twelve direct U13 EP vias. An actual filled-plane
VIN tap uses a same-layer, same-width 0.25 mm N12 output detour, adding 0.9 mm
of trace. Quiet In1 branches include the 119.5 mm analog-presence sense,
9.975 mm AUX soft-start and 9.556 mm P19-presence routes. These are actual
return-plane cuts, inventoried in `generated/native-return-layer-copper.json`;
coupled return, thermal and noise models must use this copper rather than old
snapshots. Regulator feedback remains local to its source.

All through-hole parts are front-only. C32 and C33 are the selected 10 mm WIMA
film reference capacitors. The C33 bottom-side placement defect was repaired in
the actual PCB without moving either plated pin. Both components still require
front height/seating and cropped lead inspection; the bottom assembled allowance
is only 3 mm. `assembly.py` and a mutation test reject bottom-side migration.

| Port | Local PCB location / pin contract | Role |
|---|---|---|
| J101 | (130,16), 180°; 1 DC_IN, 2 AGND | JST B2PS-VH inlet from rear E23I2; AWG16 required for catalog rating |
| J104 | 1 SWITCH_SUPPLY, 2 POWER_RUN, 3 AGND | Real JST XH3, logic-only panel-switch interface |
| J106 | 1 V2V5_AUX, 2 AGND, 3 POWER_RUN, 4 P03_ALL_SOURCES_READY | Real JST XH4 to E28 |
| J20 | (10,28), AGND | Analog return bar, Würth 7466003R M3 terminal |
| J21 | (10,14), AGND | Digital return bar, same terminal |
| J23 | (38,5.5), 5V_DIG_SRC | Operating digital positive link |
| J24 | (36,31), V5_REG_SRC | Operating analog positive link |
| J103 | Bare probe pads; no fitted header | POWER_READY probing, zero mating height in return-bar lane |

J2 retains the six original rail identities and pair/ground roles; J3 retains
digital/ground identities. Their 5 V pins are probing only. **An operating
5 V cable must not bypass the positive studs.** The retained bipolar header
still needs a selected production mating assembly and physical path acceptance.

Positive leads use selected tinned-copper Alpha 3081 AWG10 (analog, at most
190 mm installed conductor length) and Alpha 3080 AWG12 (digital, at most
110 mm), with TE SOLISTRAND 33456 M3.5 ring lugs. These limits include real bend
lengths, not just endpoint distance. Manufacturer wire bend radius, insulation
and lug/crimp geometry require the A12 harness review. Select insulation over
the crimp and a restrained cover over each live terminal. No solder-mask
insulation credit is taken at the metal supports or live thermal nodes.

The complete installed positive link must measure **≤2 mΩ**, including both
terminal solder paths, bolted joints, crimps and wire. This is a required
four-wire measurement with uncertainty and temperature correction; it is not
an assumed catalog contact resistance. The additional regulator-to-stud path
has a separate ≤1 mΩ requirement. Dedicated return bars replace the old
source-to-disconnect AGND cable edges; no phantom parallel return is retained
in the revised analysis. E28 copper and internal switch resistance remain
separate terms.

The mandatory 6 A backup fuse is on the real rear inlet. P03 F101 is removed
and its nets merged into native copper. The 4.02 kΩ guard limit uses the actual
TPS2663 full-temperature test point, giving 4.1725…4.8295 A after the declared
resistor allowance. That is not adapter/fuse/TVS fault-energy coordination.
Q101 is the P03-only logic-level PSMN012-100YL candidate; the original YS part
required a 10 V gate for its hot resistance specification, above the guard's
8.3 V minimum clamp. YL specifies 33.1 mΩ at 5 V/175 °C; the model retains a
conditional 40 mΩ allocation and requires actual hot drive/startup verification.

The AUX divider is now 11.7 kΩ + 49.9 Ω / 10 kΩ. Including the existing full
reference, resistor and FB-bias allocations gives **2.53348…2.65644 V**. E28's
conditional receiver contract is 2.50…2.70 V: only 33.48 mV remains for downward
distribution/ground/noise error and 43.56 mV for positive dynamic excursions.
These are operating allocations, not absolute-maximum acceptance. The current
model reserves 60 mA for E28, explicitly inventories native AUX resistors, and
uses a conservative 90 mA total LDO-output allocation. Active/dynamic/leakage
loads and actual harness loss remain unverified.

## Voltage, input and startup calculations

`analysis.py` reads exported native component values. Digital nominal is
5.02745 V from a real 9 kΩ + 54.9 Ω / 1 kΩ divider, centered around actual link
losses. The selected 9 kΩ/1 kΩ Susumu parts are 0.01%/2 ppm; the model retains
a conservative **0.1% total resistor-error allocation**, including unverified
assembly/aging remainder. The small series trim has a separate 0.3% allocation;
the enclosing divider calculation uses 0.102%. The marking alone does not
establish a lifetime guarantee. TPS543620 feedback bias has no guaranteed
maximum in the consulted table; the 100 nA model bound remains an explicit
qualification requirement.

For every endpoint, the lower voltage subtracts the allocated dynamic/spreading
terms and all independent positive load-current times positive-path resistance
plus the upper return-transfer impedance. The upper voltage adds all independent
negative return currents times that same transfer bound. The return model uses
Rayleigh monotonicity and effective-resistance polarization for every independent
edge resistance in [0,Rmax], rather than treating the all-hot network as the
worst transfer-impedance corner. Positive and negative analog loads never cancel
by assumption. E28 uses four digital and three analog TPS259482L devices, giving
20 mΩ/N only after every branch is on; measured branch copper is additional.

The protected-input operating scenario is 9.8…13.2 V. The full feed must include
the rear jack, mandatory fuse, two VH mated connectors, cable, PCB copper,
external blocking FET and internal eFuse. Four VH contact interfaces alone
contribute up to 80 mΩ from the environmental catalog limit. `feed_scenario`
uses a clearly unverified 0.36 Ω aggregate allocation and solves the stable
constant-power quadratic, including auxiliary current. It does not substitute
nominal 12 V current for actual low-input current. Selected hot fuse/jack/wire
bounds and native input-copper extraction are still needed to close the chain.

Original PG divider 73.2 kΩ/10 kΩ could require 10.2486 V at its worst corner.
R105 is now 68.1 kΩ, with worst PG assertion below 9.8 V. A real LTC2910H and
SN74LVC1G97 Schmitt AND stage monitor all six rails, input and both buck PG outputs and
provide a conditional 56.8 ms lower debounce allocation including initial and
C0G temperature tolerance. Scaling the 1 nF timing table to the native 10 nF,
leakage and contamination remain unverified. The negative input-offset network is
solved simultaneously, including REF grounded/floating with charged negative
rails; this is not approximated by an unbounded Schottky clamp. Presence READY
is only a prerequisite for E28's controlled staged startup, not audio unmute or
precision load-window health.

J106.4 `P03_ALL_SOURCES_READY` is U25's open-drain RESET output; the internal
`P03_SOURCES_READY` net is the separate buck-PG signal. R316 is now 2.2 kΩ,
selected Panasonic ERA6AEB222V. The paired E28 interface requires a 15 kΩ
pulldown and one Schmitt input before buffered fanout. With ±3%/±2% total
resistance allocations, 20 µA receiver leakage and an additional unverified
2 µA source-off/contamination allowance, HIGH is at least 2.152 V against a
2.0 V requirement. Open harness is at most 0.306 V against 0.4 V. The source
LOW load is below 1.27 mA, within the LTC2910's 2.5 mA/0.3 V test condition
at VCC 2.3 V. Below that supply, E28's independent AUX supervisor must mask
READY. Off leakage, ground/wire/noise offsets, transition timing, contamination
and partial power remain unqualified. No ordinary LVC slow-edge assumption is
carried forward.

The buck input-layout repair replaces four nominal 100 nF bypasses with exact
TDK C2012X7R1H225K125AC 2.2 µF/50 V/0805 parts, requiring at least 1 µF effective
at each VIN pair over the declared operating/lifetime conditions. Four separate
C1005X7R1H104K050BB 100 nF/50 V/0402 bypasses provide the same-face HF role.
The earlier a913 checkpoint omitted these separate HF parts; its native files
and evidence are preserved before this correction. Selected
C2012X7R1E475K125AB 4.7 µF/25 V/0805 BP5 parts make room for these local lands;
BP5 still requires at least 2.2 µF effective. Both bodies have 1.45 mm maximum
height plus a 0.10 mm seating allocation. Eight front capacitor placements and
sixteen direct 0.35 mm front copper links are authored in `buck_layout.py`.
The 18.2 kΩ MODE parts select the 4 pF ramp, high current limit and nominal
4 ms startup. `buck_control.py` records actual settings and LC/transient screens.
Its full 2.4 A step example exceeds the local minimum-capacitance estimate;
downstream bulk cannot be credited as an ideal parallel capacitor through
finite switches and wiring. A coupled PDN/loop model, effective-capacitance
bounds, switching jitter and measured phase/gain margins remain required.

The internal open-drain PG receivers now use a real six-pin SN74LVC1G97DBVR,
configured with In1 grounded so its truth table is AND. Its two local supply
bypasses and the external READY pullup are deliberately placed in
`control_layout.py`. `internal_pg.py` keeps the continuous AUX threshold
enclosure as an explicit inference between published 2.3 V/3.0 V rows.
The buck-PG LOW row is tested at 12 V input; its use across the actual input
window, the 80 mV inferred LOW margin, slow ramps, noise and partial power
remain verification items. This internal Schmitt stage is separate from E28's
external READY receiver. C63 rotates 180 degrees within its original physical
envelope to put its switch terminal toward U13 and its coupling node toward D4;
the actual pin order and native copper are recorded in `cuk-port-order.json`.

E28's first digital master charges the full digital capacitance before followers
turn on; only the fourth digital SPLYGD permits the analog master. The model
keeps full 2.4 A/0.251 A constant loads present during ramp. It never divides
charging capacitance by the final parallel count. Complete-capacitance scenarios
of 7.1 mF digital and 2.2 mF analog include unverified downstream allocations;
the known native subtotal is kept separate. Master transient thermal/SOA,
partial power, explicit EN reset on OV recovery, overload recovery, and the
raw-converter startup waveform still require verification. A typical 4 ms buck
soft start is not a guaranteed minimum ramp time.

The four bipolar banks require separate controlled startup. Si8751 MCAP is an
OFF-state Miller clamp and does not bound their charging current. The native
source/bleed/control ledger is in `generated/bipolar-ledger.json`; its 151 mA per
±12 V and 26 mA per ±19 V external loads still require current closure against
the latest downstream boards. The old independent 50 mA RAW_N22 allocation is
insufficient for the conservative ledger. Per-converter phase power is reported
separately, so spare power in U13 cannot conceal a U1 transient.

LM5067/LM5069 proposals using large shunts were rejected: both manufacturers
require sense resistance no greater than 100 mΩ. The unimplemented R40=181 kΩ
N12 recenter and LTC4252A 264.73 mA current-limit trial leave only about 30.6 mV
raw-droop allowance after the chosen LDO headroom, even at the LT3471's 25 °C
current-limit screen. Hot current limit/frequency, raw-ripple and transient
stability are not guaranteed by that arithmetic. No bipolar startup capacity
or controller implementation is qualified by the positive-5 V startup model.

## Native evidence and remaining work

`thermal.py` implements actual same-node spreader zones and via fields, carries
over the quiet-plane exclusions, and inventories current native vias in
`generated/heatmap.json`. The count alone is insufficient: filled connected
spreader area, package resistance, hot plated-barrel conductivity, lateral
spreading, TIM thickness/contact pressure, interfaces and external convection
must form a complete temperature bound. Live P12, RAW_N17, RAW_N22 and input-FET
thermal nodes remain electrically isolated from the A12 metal base.

The low-raw negative feedback parts now form a B-side row at local X97.5,
outside the underside TIM cut. Quiet LO_REF_1V/LO_N_FB source escapes may use
In2.Cu through the contact field; their actual clearance voids receive no AGND
thermal-conduction credit. All twelve direct EP vias remain. C72 is the local
100 nF VREF bypass, now an exact TDK C1005X7R1H104K050BB on F.Cu beside U13.
C73 remains the original 68 pF positive compensation capacitor. Native value/net
mutation tests explicitly reject exchanging these roles. The feedback repair
invalidates earlier thermal/ground/MCAD receipts until their actual source
snapshots are regenerated.

The heat map includes Q101's 0.64 W allocation and the native −14 V change.
Its revised conservative provision is about **10.56 W**. An explicit erratum
replaces U102's old 0.7 W with 0.9613 W to enclose the 90 mA output allocation;
U10 now uses the same conservative 22.5 mA LT3090 ground-current envelope as
the bipolar ledger, increasing its screen from 0.2142 W to 0.6292 W. These
allocations supersede the earlier 9.87 W whole-base screen. Some converter
allocations conservatively put total converter loss at the IC and must not be
double-counted again at their inductors/diodes. The previous 35 µm inner-layer native snapshot is retained compressed in
`generated/history/` with its original hash and stackup. Published typical TIM or JEDEC
thermal values do not qualify the actual board or junctions.

Meaningful mutation/boundary tests are in `tests/tooling/test_power_p03.py`.
They exercise pin/tab swaps, old PG/AUX values, partial-power input violation,
missing parallel branches, raw-rail dropout/duty, feed collapse and startup
capacitance. Native verification must be rerun after final routing, local
thermal via access, copper/ampacity/hot-loop extraction, exact effective-capacity
MPN selection and connector/assembly review. All physical, startup, thermal,
ampacity and fabrication release flags remain false. An isolated supply test
does not need a firmware image.

Primary references are stored as component source URLs: TI TPS543620 Rev C,
TPS2663 Rev G, TPS25948 Rev D; ADI LT3045, LT3471 Rev C, LT3080 Rev C, LT3090
Rev A and LTC2910 Rev C; the Susumu RG_LL data sheet; JST VH catalog; Würth
7466003R drawing; Alpha 3080/3081 specifications; TE 33456 drawing/application
instructions. A reviewed exact land/stencil and accepted stackup are required
before fabrication; source attribution alone is not an approval.

The selected input-feed calculation now binds A12's actual adapter/harness JSON.
The MEAN WELL output tolerance boundary is the adapter plug, so its captive
output cable is not counted a second time. Catalog contact figures, native
copper screens, unmeasured hot fuse/copper allocations and actual measurements
remain distinct. The 0.36 ohm complete-feed scenario has an explicitly unproved
remainder and does not bound adapter startup droop.

`models.capacitors()` labels its compatibility subtotal as initial tolerance only.
Separate declared-dielectric temperature factors are included for X7R/X7S/C0G;
unselected generic/electrolytic temperature/lifetime bounds remain missing. A
partial known inventory is never a complete maximum-capacitance qualification.
The disconnect dV/dt calculation includes the C0G −0.3% temperature factor.

The canonical unreleased construction is now C50: 1.6 mm total thickness,
85 µm outer / 70 µm inner minimum finished copper and 50 µm minimum plated
through-wall, resin filled and copper capped. Its 12 direct U13 EP lands are
0.70 mm with 0.25 mm finished bores at the original 0.50 mm pitch. The explicit
`construction.json` binds the native PCB and records missing maximum plating,
drill/registration/etch, finished bore and drill-web approvals. The general
0.60/0.25 mm vias retain only 0.125 mm example preplate annulus at 50 µm wall;
this is a board-wide custom DFM requirement. The initial `construction50/`
native snapshot is frozen for comparison; the prior 25 µm source is archived.
None of these requirements is an accepted fabricator process or a measured
thermal qualification.
