# Standalone verification record

The [build record](build.json) captures source hashes, the firmware binary hash,
ARM section sizes and nine passing host suites. The [F04 record](external-firmware.json)
captures both current firmware profiles and converter/input-policy checks.
The [memory profile](host-memory.json)
records engine/factory-bank heap payload at 48 and 96 kHz. These are host/build
checks, not physical unit tests.

Packaged historical firmware and review ZIPs are listed in the [release catalog](../releases/README.md), with checksums and recovery instructions. Historical records retain their original snapshot paths and hashes.

| Check | Evidence | Scope / limit |
| --- | --- | --- |
| Existing DSP | CTest `engine` | Rates, finite output, allocations and existing control checks |
| Physical controls | CTest `hardware_controls` | Scene/source actions, nudge, bank, release, selected-pad rolls, Hold, long presses and feedback |
| F04 control expanders | CTest `control_expanders`, [pin map](../firmware/control-inputs.json) and same ARM/profile record | All32 physical front inputs,4,096 mixed frames,unused/output-only/rear pin isolation,both profile configurations,failed bus/readback setup and incomplete-frame rejection; three MCP23017s and E18 receiving-load contract checked; physical scan/EMI unverified |
| E18 digital input hub | [Native record](../electronics/control_inputs/generated/verification.json), [PCB packet](../electronics/control_inputs/generated/placement.json) and [connector map](../electronics/control_inputs/generated/connector-map.csv) |15 independent contracts,32 front/four rear inputs,zero ERC/DRC/parity/open connections,424 segments,62 vias,filled AGND plane,fresh E09/E11 interfaces and F04 mapping; no physical scan/EMI/fit proof; remaining control circuits unfinished |
| External arena | CTest `audio_arena` | Alignment, reuse, payload preservation, free/coalescing and exhaustion |
| Wire mapping | CTest `hardware_wire` | LED bit order, lever wrap/direction and touch centroid |
| Connection gain switching | CTest `connection_mode` | Immediate bypass request, debounce, dry wait, gain settling, bounce, delayed polling and timer wrap |
| Hardware latch feedback | CTest `relay_feedback` | Initial arming, lost feedback, stable rearm after bypass, switch-pole delay, deliberate bypass and timer wrap |
| F03 external converter | CTest `external_converter` and [ARM/profile record](external-firmware.json) | 312 injected setup/activation/configuration faults; bounded delayed-power ID probing, wrong/missing/chattering device and timer-wrap checks; paired latching/reserved bits, silent startup, delayed/interrupted settling, live clocks/ramp, relay policy, calibration restart, qualified PCM/DMA boundaries; both builds cross-compile, no hardware timing/audio evidence |
| F02 input qualification | CTest `input_qualification` and same ARM/profile record | 1.25s continuous quiet,10s timeout/chatter, bus faults, calibration, late status loss, actual gain/rearm/feedback integration, manual bypass and timer wrap |
| Circuit constraints | [E01 calculation record](../electronics/generated/line-levels.json) and [fault-latch scenarios](../electronics/generated/bypass-logic.json) | Ideal headroom/logic calculations; no electrical, SPICE, ERC or bench evidence |
| Embedded application | ARM ELF/bin and sections in `build.json` | Cross-compiles with pinned actual SDK; not run on Seed3 |
| Mechanical solids | [CAD report](../cad/generated/solid-validation.json) | Seven closed, consistently wound, connected positive-volume STL parts |
| Lever motion | Same CAD report | Expanded convex sweep through 0-35 degrees; excludes spring/fasteners/wiring |
| Internal placement | [Reserve check](../cad/generated/internal-clearance.json) | Named conservative boxes and mounts, including actual E07 output-board positions; no physical wire-fit evidence |
| B01 button hard parts | [Button mesh/motion report](../cad/generated/button-solid-validation.json) | Eight connected closed solids; continuous rigid travel against guide/panel; excludes compliant contacts, spring and printed fit |
| B01 passive test PCB | [Native KiCad record](../electronics/button_test/generated/verification.json) | Zero ERC/DRC/unconnected/parity issues and checked exported pin pairs; not the full control PCB |
| E02 watchdog/driver schematic | [Native record](../electronics/bypass/generated/verification.json) | Zero ERC issues, package-pin contract and 25 exported-netlist ideal fault scenarios; no PCB/bench proof |
| E03 stereo bypass contacts | [Native record](../electronics/audio_bypass/generated/verification.json) | Zero ERC, exact exported pin nets, four settled relay combinations, fresh E02 coil-interface check and nominal relay land-pattern audit; no PCB/bench proof |
| E04 audio architecture | [Noise/gain/supply screen](../electronics/generated/audio-budget.json) | Rejects approval of the prototype converter/E01 network under stated assumptions; external codec and ±19 V driver candidates still need circuits, firmware and physical measurements |
| E05 post-receiver output stage | [Native record](../electronics/output_stage/generated/verification.json) and [circuit analysis](../electronics/output_stage/generated/circuit-analysis.json) | Zero ERC, exact pins/interfaces, 12 ideal AC/four ideal DC cases, 256 tolerance cases and conditional power/noise/voltage screens; routing checked separately under E07; full analog circuit and bench work incomplete |
| E07 routed output board | [Routing record](../electronics/output_stage/generated/routing-verification.json) | 41 actual footprints, four mounting holes, 211 segments, 45 vias and saved AGND fill; zero all-severity DRC/library/parity issues and zero open connections; final stackup/parts and physical audio open |
| E08 DAC I/V / receiver | [Native record](../electronics/dac_receiver/generated/verification.json) and [circuit analysis](../electronics/dac_receiver/generated/circuit-analysis.json) | 60 exact component contracts, zero ERC, fresh E05 load/interface, 24 ideal AC and 32 DC cases, 16,384 listed passive/source corners and 12 ideal output-cascade cases; hypothetical DAC normalization, no complete codec, PCB/placement or physical audio proof |
| E09 converter core / qualification | [Native record](../electronics/converter/generated/verification.json) and [electrical screens](../electronics/converter/generated/electrical-screens.json) | 60 component contracts, 49 codec pins, zero ERC, fresh E08/E02 interfaces, 256 powered logic cases and conditional timer minimum1.21 s; proposed pin-plan resource audit against pinned SDK; F01 firmware checked separately; codec footprint, PCB/placement and physical performance unfinished |
| A04 output/input-hub fit | [CAD report](../cad/generated/solid-validation.json) and [reserve report](../cad/generated/internal-clearance.json) | Seven checked solids; empty native output/input-hub intersections against shell,other boards,control/lead/scene-PCB reserves;241 nonintersecting named reserves and lever sweep; conditional dimensions/assembly,carrier drill/keepout proposal only; no physical fit or complete electronics placement |
| E10 input range / preamplifier | [Native record](../electronics/input_range/generated/verification.json) and [circuit screens](../electronics/input_range/generated/circuit-analysis.json) | Historical E10 snapshot:28 exported pin/value contracts, zero ERC,24 loaded AC/64 allocated DC cases,1,024 mode/tolerance cases; precharge implementation followed in E11/F02; ADC driver/bias/protection, PCB/placement and physical performance remain open |
| E11 independent relay/input sequence | [Native record](../electronics/sequenced_bypass/generated/verification.json) and [conditional screens](../electronics/sequenced_bypass/generated/electrical-screens.json) | 55 exact exported contracts,zero ERC,256 powered cases,seven fault/startup/gain sequences,fresh E10/E05/E09 interfaces; startup, pulse and mechanical timing allocations need measurement; no PCB/placement/physical proof |
| E12 ADC driver/reference servo | [Native record](../electronics/adc_driver/generated/verification.json) and [circuit screens](../electronics/adc_driver/generated/circuit-analysis.json) | 79 exact exported contracts,zero ERC,18 ideal AC,192 resistor/load corners,128 allocated DC,512 DC superposition bounds and36 hypothetical finite-model cases; actual ADC load/stability, scale/protection, weighted system noise, PCB/placement and physical performance remain open |

| E13 independent rail/bias windows | [Native record](../electronics/rail_monitor/generated/verification.json) and [electrical screens](../electronics/rail_monitor/generated/electrical-screens.json) | 181 exact exported contracts, zero ERC, eight windows/73,728 allocated threshold corners, 131,072 powered logic combinations, fresh E09/E11/E12 interfaces and wider-rail conditional headroom; reference/bias loading checked; offsets/leakage/startup include allocations; main power generation/disconnects, PCB/placement and physical timing/audio remain open |

| E14 main rail generation | [Native record](../electronics/power_supply/generated/verification.json) and [electrical screens](../electronics/power_supply/generated/electrical-screens.json) | E17 adaptation:157 exact exported contracts, zero ERC,1,280 allocated linear/32 buck/128 raw-setpoint corners,192 hypothetical SET-source loops,actual amplifier census and E08 load-current screen; source names end in_SRC and R51 trims digital source5.004V; E17 checks protected voltage drop; actual stability/ripple/thermal,complete placement and physical power/audio remain open |

| E16 input protection / fast-OV / enable guard | [Native record](../electronics/input_protection/generated/verification.json) and [electrical screens](../electronics/input_protection/generated/electrical-screens.json) | E17 adaptation:48 exact contracts,zero ERC,80 eFuse/2,048 fast-OV threshold corners,11 conditional settled states and fresh E14/E17 exports; J6 feeds65mA downstream AUX allocation and checked100k run receiver; actual delay/charge,current,RF/thermal and regulator transients remain open; no PCB/physical proof |

| E17 six-rail disconnect / OV-only interlock | [Native record](../electronics/rail_disconnect/generated/verification.json) and [electrical screens](../electronics/rail_disconnect/generated/electrical-screens.json) | 162 complete exported component/net/value contracts,zero ERC,16,384 threshold corners,512 powered interlock combinations,768 ideal body-diode direction cases,reference-open bleed and fresh source/load interfaces; protected-star voltage-drop targets retained; conditional125us charge screen includes failing stress cases; Si8751 timing uses100pF and does not bound actual FETs; fault currents,timing,stability,inrush,partial power/aging,PCB/fit and physical tests remain open |

The firmware reserves 48 MiB of SDRAM. Linked code and internal static data fit
the SDK regions; processor timing, stack high-water marks, interrupt behavior and
physical memory stability remain unmeasured. The firmware guide records the
SDK/newlib syscall and SRAM linker warnings.

Open gates include PCB design/assembly, physical control fit, sensor calibration,
LED optics, boot/power behavior, watchdog/bypass operation, round-trip latency,
gain/headroom, noise/distortion, thermal behavior and a two-hour hardware soak.
Sample/preset storage and user settings application still need implementation.
