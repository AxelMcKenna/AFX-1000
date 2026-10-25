# Standalone verification record

The historical [A04/E18 build record](build.json) captures source hashes, the firmware binary hash,
ARM section sizes and nine passing host suites. The [F04 record](external-firmware.json)
captures both firmware profiles and converter/input-policy checks for its packaged source snapshot.
The separate [A05/E19 processor and housing record](processor-housing.json) captures its PCB/CAD update; it makes no new ARM, audio or physical-test claim.
The [A06/E20 LED and housing record](led-housing.json) captures the routed
96-channel driver, updated component reserves and explicit firmware latch
guards. Its power reconciliation reports failed system-load/startup/drop
allocations; this remains a design review, not an assembly release.
The [E21 power-load update](power-load.json) revises the digital provision,
input current/ramp and parallel FET bank. Its conditional screens include E20
once and preserve the normal voltage targets. All-rail startup/late closure,
increased gate charge, large-capacitor loop, thermal/distribution limits and
physical qualification remain open. It makes no new firmware-build claim.
The historical [E22 input-board update](input-board.json) adds a routed 48-part DC inlet,
eFuse and fast-shutdown PCB. Its native PCB checks and measured local shutdown
trace supplement the E21 circuit evidence. Rear-wall/actuator integration,
stackup/thermal/current qualification and physical protection tests remain open.
The [A07/E23 housing/input-board update](input-housing.json) adds rear-edge and
output-board profile reliefs, four matched mounts and inlet/switch apertures.
Its 690 reserves, seven native solids and lever/board intersection checks pass;
the input assembly has an empty intersection against the housing and rear plate.
Twenty-four tooling tests pass, including rejection of the earlier recessed
jack and switch positions. Exact mating/feel, assembly and electrical/thermal
qualification remain open. No new firmware build is claimed.
The historical [E24 main-power placement record](main-power-placement.json) adds 157 placed
components, four mounting holes, checked inductor lands and selected inductor/
film-capacitor candidates. Nonrouting DRC and parity pass with 333 open
connections. Copper, hot-loop/thermal/EMI work and housing integration remain
open. The A07 CAD packet and earlier routed boards are unchanged.
Twenty-six tooling tests pass, including wrong-inductor-land and through-hole
thermal-region regressions. No new ARM build or mechanical render is claimed.
The [current main-power routing record](main-power-routing.json) covers both bucks, both bipolar raw generators, the +19 V/+12 V/analog 5 V linear stages, the negative reference and DC target paths. The candidate grows to 90 × 44 mm, preserving the E24 parent. Its 2,600 segments, 285 vias and seven saved fills pass native DRC/parity with zero open connections. All 322 path measurements and 135 tooling tests pass. SET Kelvin separation, output-tab/header feeds, 31 quiet-return antipads, quiet-to-power contact clearances and the negative-reference copper return domain are checked. A10 integrates the current component positions; native solids/sweeps/collisions and seven integration regressions pass under provisional heights. A09 keeps frozen supply inputs and its seven historical regressions pass. Actual loss/stability/thermal/EMI and physical qualification remain open.
The [memory profile](host-memory.json)
records engine/factory-bank heap payload at 48 and 96 kHz. These are host/build
checks, not physical unit tests.

Packaged historical firmware and review ZIPs now live in the [release artifact catalog](../releases/README.md). Its manifest maps original paths to local archive locations and records checksums and recovery sources. Historical records below retain the paths and hashes of their original snapshot; current build instructions are in the [hardware guide](../README.md).

| Check | Evidence | Scope / limit |
| --- | --- | --- |
| Main-supply routing in progress | [Copper record](../electronics/power_supply/routing/generated/verification.json) and [scope](../electronics/power_supply/routing/README.md) | 90 × 44 mm: both bucks, both raw generators, all positive linear rails, negative reference and DC target paths; 2,600 segments, 285 vias, seven fills, zero opens, 322 path graphs, zero native DRC/parity issues and 135 tooling tests. Kelvin separation, physical output-tab/header feeds and quiet-to-power contacts checked. Electrical/physical qualification and other standalone boards remain open |
| E25/A11 disconnect placement and source wiring | [Record](disconnect-placement.json), [E25 scope](../electronics/rail_disconnect/placement/README.md), [A11](../cad/a11/README.md), [wiring](../wiring/README.md) | 164 parts; zero native nonrouting DRC/parity, 365 opens; 54 A11 solids/117 copies and eight collision checks pass. 150 tooling/23 CAD integration tests pass. Eleven power/control pin pairs checked; trial 18 AWG supply wiring fails remaining analog/digital 5 V loss budgets. E25 routing, production distribution and physical qualification remain open |
| E24 main-supply placement | [Placement record](../electronics/power_supply/generated/placement-verification.json), [PCB packet](../electronics/power_supply/generated/placement.json) and [part screen](../electronics/power_supply/generated/part-selection.json) | 157 parts, four holes, six proposed layers and 84 × 38 mm outline; zero nonrouting DRC/parity issues, 333 open connections. No tracks/vias/planes. Positive OUT and negative IN exposed pads checked independently. Inductor lands checked against manufacturer dimensions; current/bias/thermal limits remain unqualified. No housing-fit or build-ready claim |
| E23 DC input/protection PCB and A07 placement | [PCB record](../electronics/input_protection/generated/routing-verification.json), [PCB packet](../electronics/input_protection/generated/placement.json) and [housing packet](../cad/generated/input-power-placement.json) | 48 circuit parts, four M2 holes, relieved 64 × 44 × 1.6 mm profile, four layers, 763 segments/125 vias, two saved AGND fills; zero native DRC/parity/open items. Q3-to-SHDN F.Cu path 7.05 mm. Native input/housing/rear-plate intersection empty; full-unit power, ampacity, thermal, physical protection/mating/assembly remain unqualified |
| Existing DSP | CTest `engine` | Rates, finite output, allocations and existing control checks |
| Physical controls | CTest `hardware_controls` | Scene/source actions, nudge, bank, release, selected-pad rolls, Hold, long presses and feedback |
| F04 control expanders | CTest `control_expanders`, [pin map](../firmware/control-inputs.json) and same ARM/profile record | All32 physical front inputs,4,096 mixed frames,unused/output-only/rear pin isolation,both profile configurations,failed bus/readback setup and incomplete-frame rejection; three MCP23017s and E18 receiving-load contract checked; physical scan/EMI unverified |
| E18 digital input hub | [Native record](../electronics/control_inputs/generated/verification.json), [PCB packet](../electronics/control_inputs/generated/placement.json) and [connector map](../electronics/control_inputs/generated/connector-map.csv) |15 independent contracts,32 front/four rear inputs,zero ERC/DRC/parity/open connections,424 segments,62 vias,filled AGND plane,fresh E09/E11 interfaces and F04 mapping; no physical scan/EMI/fit proof; remaining control circuits unfinished |
| E19 processor/knob carrier | [Native record](../electronics/processor_carrier/generated/verification.json), [placement](../electronics/processor_carrier/generated/placement.json) and [connectors](../electronics/processor_carrier/generated/connector-map.csv) |76 parts,40 module pins,ten knob interfaces,eight holes/copper keepouts; zero native ERC/DRC/parity/open; short bottom-only ADC networks; current F04/E09/E11/E17/E18 contracts pass; electrical/physical qualification and remaining control boards unfinished |
| E20 LED/display driver | [Native record](../electronics/led_driver/generated/verification.json), [placement](../electronics/led_driver/generated/placement.json), [channel map](../electronics/led_driver/generated/channel-map.csv) and [power reconciliation](../electronics/led_driver/generated/power-reconciliation.json) |49 parts,96 sinks,six layers,two filled ground planes,3,508 segments,239 vias; zero native ERC/DRC/parity/open; fresh E19 interface and explicit latch guards checked. A06 includes its four mounts and component/harness/lead bounds. Emitters, optics, harnesses, power integration and physical qualification remain open |
| External arena | CTest `audio_arena` | Alignment, reuse, payload preservation, free/coalescing and exhaustion |
| Wire mapping | CTest `hardware_wire` | All1,152 PWM bits walked through four independent modeled shift registers, LED order, lever wrap/direction and touch centroid; no physical timing proof |
| Connection gain switching | CTest `connection_mode` | Immediate bypass request, debounce, dry wait, gain settling, bounce, delayed polling and timer wrap |
| Hardware latch feedback | CTest `relay_feedback` | Initial arming, lost feedback, stable rearm after bypass, switch-pole delay, deliberate bypass and timer wrap |
| F03 external converter | CTest `external_converter` and [ARM/profile record](external-firmware.json) | 312 injected setup/activation/configuration faults; bounded delayed-power ID probing, wrong/missing/chattering device and timer-wrap checks; paired latching/reserved bits, silent startup, delayed/interrupted settling, live clocks/ramp, relay policy, calibration restart, qualified PCM/DMA boundaries; both builds cross-compile, no hardware timing/audio evidence |
| F02 input qualification | CTest `input_qualification` and same ARM/profile record | 1.25s continuous quiet,10s timeout/chatter, bus faults, calibration, late status loss, actual gain/rearm/feedback integration, manual bypass and timer wrap |
| Circuit constraints | [E01 calculation record](../electronics/generated/line-levels.json) and [fault-latch scenarios](../electronics/generated/bypass-logic.json) | Ideal headroom/logic calculations; no electrical, SPICE, ERC or bench evidence |
| Embedded application | ARM ELF/bin and sections in `build.json` | Cross-compiles with pinned actual SDK; not run on Seed3 |
| Mechanical solids | [CAD report](../cad/generated/solid-validation.json) | Seven closed, consistently wound, connected positive-volume STL parts |
| Lever motion | Same CAD report | Expanded convex sweep through 0-35 degrees; excludes spring/fasteners/wiring |
| Internal placement | [Reserve check](../cad/generated/internal-clearance.json) | A07:690 named conservative boxes and mounts, including actual E07/E18/E19/E20/E23 bounds and input PCB reliefs; no physical wire-fit evidence |
| B01 button hard parts | [Button mesh/motion report](../cad/generated/button-solid-validation.json) | Eight connected closed solids; continuous rigid travel against guide/panel; excludes compliant contacts, spring and printed fit |
| B01 passive test PCB | [Native KiCad record](../electronics/button_test/generated/verification.json) | Zero ERC/DRC/unconnected/parity issues and checked exported pin pairs; not the full control PCB |
| E02 watchdog/driver schematic | [Native record](../electronics/bypass/generated/verification.json) | Zero ERC issues, package-pin contract and 25 exported-netlist ideal fault scenarios; no PCB/bench proof |
| E03 stereo bypass contacts | [Native record](../electronics/audio_bypass/generated/verification.json) | Zero ERC, exact exported pin nets, four settled relay combinations, fresh E02 coil-interface check and nominal relay land-pattern audit; no PCB/bench proof |
| E04 audio architecture | [Noise/gain/supply screen](../electronics/generated/audio-budget.json) | Rejects approval of the prototype converter/E01 network under stated assumptions; external codec and ±19 V driver candidates still need circuits, firmware and physical measurements |
| E05 post-receiver output stage | [Native record](../electronics/output_stage/generated/verification.json) and [circuit analysis](../electronics/output_stage/generated/circuit-analysis.json) | Zero ERC, exact pins/interfaces, 12 ideal AC/four ideal DC cases, 256 tolerance cases and conditional power/noise/voltage screens; routing checked separately under E07; full analog circuit and bench work incomplete |
| E07 routed output board | [Routing record](../electronics/output_stage/generated/routing-verification.json) | 41 actual footprints, four mounting holes, 211 segments, 45 vias and saved AGND fill; zero all-severity DRC/library/parity issues and zero open connections; final stackup/parts and physical audio open |
| E08 DAC I/V / receiver | [Native record](../electronics/dac_receiver/generated/verification.json) and [circuit analysis](../electronics/dac_receiver/generated/circuit-analysis.json) | 60 exact component contracts, zero ERC, fresh E05 load/interface, 24 ideal AC and 32 DC cases, 16,384 listed passive/source corners and 12 ideal output-cascade cases; hypothetical DAC normalization, no complete codec, PCB/placement or physical audio proof |
| E09 converter core / qualification | [Native record](../electronics/converter/generated/verification.json) and [electrical screens](../electronics/converter/generated/electrical-screens.json) | 60 component contracts, 49 codec pins, zero ERC, fresh E08/E02 interfaces, 256 powered logic cases and conditional timer minimum1.21 s; proposed pin-plan resource audit against pinned SDK; F01 firmware checked separately; codec footprint, PCB/placement and physical performance unfinished |
| A05 output/input/processor fit | [CAD report](../cad/generated/solid-validation.json) and [reserve report](../cad/generated/internal-clearance.json) | Seven checked solids;451 named reserves; lever/output intersections empty; control/carrier intersections restricted to intended mounting-face contacts; matching E19/E18 holes and fixing bounds implemented; complete electronics, exact parts, wiring and physical fit unfinished |
| E10 input range / preamplifier | [Native record](../electronics/input_range/generated/verification.json) and [circuit screens](../electronics/input_range/generated/circuit-analysis.json) | Historical E10 snapshot:28 exported pin/value contracts, zero ERC,24 loaded AC/64 allocated DC cases,1,024 mode/tolerance cases; precharge implementation followed in E11/F02; ADC driver/bias/protection, PCB/placement and physical performance remain open |
| E11 independent relay/input sequence | [Native record](../electronics/sequenced_bypass/generated/verification.json) and [conditional screens](../electronics/sequenced_bypass/generated/electrical-screens.json) | 55 exact exported contracts,zero ERC,256 powered cases,seven fault/startup/gain sequences,fresh E10/E05/E09 interfaces; startup, pulse and mechanical timing allocations need measurement; no PCB/placement/physical proof |
| E12 ADC driver/reference servo | [Native record](../electronics/adc_driver/generated/verification.json) and [circuit screens](../electronics/adc_driver/generated/circuit-analysis.json) | 79 exact exported contracts,zero ERC,18 ideal AC,192 resistor/load corners,128 allocated DC,512 DC superposition bounds and36 hypothetical finite-model cases; actual ADC load/stability, scale/protection, weighted system noise, PCB/placement and physical performance remain open |

| E13 independent rail/bias windows | [Native record](../electronics/rail_monitor/generated/verification.json) and [electrical screens](../electronics/rail_monitor/generated/electrical-screens.json) | 181 exact exported contracts, zero ERC, eight windows/73,728 allocated threshold corners, 131,072 powered logic combinations, fresh E09/E11/E12 interfaces and wider-rail conditional headroom; reference/bias loading checked; offsets/leakage/startup include allocations; main power generation/disconnects, PCB/placement and physical timing/audio remain open |

| E14 main rail generation | [Native record](../electronics/power_supply/generated/verification.json) and [electrical screens](../electronics/power_supply/generated/electrical-screens.json) | E21:157 exact contracts,zero ERC,1,280 allocated linear/32 buck/128 raw-setpoint corners,192 hypothetical SET-source loops;1.574A digital load against1.8A provision;1uF digital soft start screens a preconnected6.5mF allocation; all-rail startup,large-capacitor loop,ripple/thermal,placement and physical qualification remain open |

| E16 input protection / fast-OV / enable guard | [Native record](../electronics/input_protection/generated/verification.json) and [electrical screens](../electronics/input_protection/generated/electrical-screens.json) | E21:48 exact contracts,zero ERC,80 eFuse/2,048 fast-OV threshold corners,11 settled cases;5.62k current setting,330nF ramp; conditional steady/bus/preconnected-digital charging2.773A against2.874A minimum allocation. Other-rail charging,late closure,real current limit,fault/SOA,thermal and physical proof remain open |

| E17 six-rail disconnect / OV-only interlock | [Native record](../electronics/rail_disconnect/generated/verification.json) and [electrical screens](../electronics/rail_disconnect/generated/electrical-screens.json) | E21:164 exact contracts,zero ERC,16,384 threshold corners,512 interlock combinations,768 common-gate diode-direction cases and16 independent digital gate states; Q11/Q13 and Q12/Q14 parallel digital legs. At1.801A,allocated range4.9028–5.0992V preserves4.9–5.1V target. Digital gate load doubles;100pF timing is not a bound for actual FETs. Fault/timing,loop,all-rail startup,thermal,distribution,PCB/fit and physical tests remain open |

The firmware reserves 48 MiB of SDRAM. Linked code and internal static data fit
the SDK regions; processor timing, stack high-water marks, interrupt behavior and
physical memory stability remain unmeasured. The firmware guide records the
SDK/newlib syscall and SRAM linker warnings.

Open gates include PCB design/assembly, physical control fit, sensor calibration,
LED optics, boot/power behavior, watchdog/bypass operation, round-trip latency,
gain/headroom, noise/distortion, thermal behavior and a two-hour hardware soak.
Sample/preset storage and user settings application still need implementation.
