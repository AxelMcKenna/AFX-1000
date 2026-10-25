# Standalone RMX hardware

Preserved from `hardware/README.md` on 23 October 2026. This records the earlier design discussion; current setup and status are linked from the [repository guide](../../../README.md). Existing source citations have been carried forward without new verification.

The physical unit is a standalone stereo audio effects processor. It must process
audio, run its sampler, read all performance controls, and drive its indicators
without a Mac, DAW, USB host, or network connection. USB is for service, firmware
updates and optional MIDI; it is not the audio processing architecture.

## Working architecture

Current relay/input qualification is [E11](../../../hardware/electronics/sequenced_bypass/README.md),
with [F04 firmware](../../../hardware/firmware/EXTERNAL-CONVERTER.md). E11 replaces E02/E03 for
the external converter profile. Nine host suites and both ARM builds pass;
the new circuit passes native ERC and exported logic/interface checks.
[E12](../../../hardware/electronics/adc_driver/README.md) now adds the candidate stereo ADC driver,
reference-half servos and low-voltage negative bias. Its schematic and conditional
linear checks pass; actual load/stability, protection, complete weighted noise,
integrated PCBs, placement and physical tests remain open.
[E13](../../../hardware/electronics/rail_monitor/README.md) now adds eight independent rail/bias
windows and startup qualification. Its 181-component native schematic passes ERC,
73,728 allocated threshold corners and 131,072 powered logic combinations. F03
adds bounded chip-ID probing before configuring the hardware-disabled codec;
both ARM builds and eight host suites pass. Neither the new monitor nor the
converter/input circuits have a complete PCB, enclosure placement or physical
startup/audio validation.
[E14](../../../hardware/electronics/power_supply/README.md) now has a 157-part main supply
schematic: separate ±22 V/±17 V pre-regulators, precision-controlled ±19 V/±12 V
linear stages, analog5V and a digital5V buck. Native ERC, exported topology,
allocated accuracy/dropout/current and conditional target-loop checks pass.
[E16](../../../hardware/electronics/input_protection/README.md) extends the E15 input stage to48
parts with a separate fast-OV shutdown comparator and delayed auxiliary PG.
Native ERC, exact exported contracts,80 eFuse/2,048 fast-OV threshold corners,
11 conditional settled states and fresh interfaces pass.
[E17](../../../hardware/electronics/rail_disconnect/README.md) adds162 parts for six bidirectional
rail switches and an auxiliary-powered source-OV/reference interlock. ERC,
16,384 allocated threshold corners,512 interlock combinations,768 ideal diode
direction cases and source/load interfaces pass. Source rails are distinct from
protected rails, and the digital source trim preserves its earlier load target.
Transferred fault charge, real switch timing/current, fuse/TVS coordination,
switching-loop/ripple/startup/thermal validation and all new PCB/enclosure
placement remain open. The working external12V3A adapter must deliver11.4–12.6V
at the selected inlet; the exact adapter remains unselected. The current
[A04/E18 review package](../../../hardware/releases/README.md#standalone-review-a04-e18) is a design review,
not a fabrication release.

F04 corrects the digital control wiring before PCB layout. The MCP23017's
GPA7/GPB7 are output-only in the current manufacturer specification. All32 front
inputs now use three chips across14+14+4 valid input pins; the external profile
keeps rear/status inputs on the third chip's GPA0..3. Both profiles require
three chips. Use the [wiring map](../../../hardware/firmware/control-inputs.json) or
[CSV](../../../hardware/firmware/control-inputs.csv). Configuration readback and fault checks pass.
[E18](../../../hardware/electronics/control_inputs/README.md) now implements the digital inputs
on a64 ×54mm routed daughterboard. Native ERC/DRC/parity and open-connection
checks pass. Its PCB-derived component, lead and mounting envelopes pass the
A04 CAD's241-reserve and native solid-intersection checks. All seven housing
solids remain valid in that historical review.
[E19](../../../hardware/electronics/processor_carrier/README.md) now adds a routed150 ×65mm
processor/knob carrier with76 circuit parts and eight mounting holes/keepouts.
The E18 daughterboard shifts2mm left to matching carrier holes. Native
ERC/DRC/parity/open checks pass, and A05 incorporates451 named reserves,
including the socket/module, component, solder-tail, fixing and USB bounds.
Seven housing solids and scoped native collision checks pass, allowing only
intended mounting-face contacts. Complete LED/sensor/SD circuitry, remaining
analog/power placement, exact parts, physical fit and measurements remain open.
The [A05/E19 processor and housing review](../../../hardware/releases/README.md#processor-and-housing-review-a05-e19)
captures this PCB/CAD update; the earlier A04/E18 archive retains its firmware-build evidence.

Use an embedded audio MCU/module with local RAM, stereo converters and microSD
storage. The current working candidate is **Daisy Seed3, 64 MB external SDRAM**,
running the existing portable C++ engine at **48 kHz / 128 frames**. This is a
prototype selection with hardware assembly and worst-case timing measurements
still pending. The module's higher supported sample rates do not establish that
this engine fits or meets its deadline at those rates.

The [manufacturer's Seed3 documentation](https://docs.daisy.audio/hardware/Seed3/)
provides the board specification and downloadable mechanical drawings. The
module is 51 × 18 mm, uses an STM32H750 at 480 MHz, and includes a TAC5242 stereo
codec. This is enough information to reserve board space, not proof of final
audio performance or compatibility with DJ mixer signal levels.

The [E04 audio screen](../../../research/hardware/audio-design-history.md#e04-converter-gain-and-noise-screen)
does not approve the onboard codec for the reference-performance design: under
the project's 20 dB headroom/nominal-level noise assumptions, even its optimistic
differential figures leave no budget for the minimum S/N targets. Seed3 remains
the firmware/control bring-up platform. ES9292QPRO external conversion is the
next candidate; its full circuit/PCB, procurement and physical validation
remain open. The F01 MCU adapter now cross-compiles. This does not change standalone
operation or lower the audio targets.

```text
Stereo line input ──┬── input protection / gain ── ADC ── DSP ── DAC ── output stage ──┐
                   │                                                               ├── Stereo line output
                   └──────────────── normally closed relay bypass ─────────────────┘

Controls / touch strip ── ADC + GPIO expanders ── embedded control dispatcher ── DSP
DSP / control state ── LED drivers + BPM display
microSD ── presets / samples / calibration
External low-voltage DC ── protected power input ── digital / analog supplies
Independent watchdog + power-good ── relay enable (fails to dry bypass)
```

The normally closed relay path must pass dry audio when power is absent. Relays
must select one output source at a time; processed and dry outputs must never be
hard-wired together. A watchdog circuit must remove relay enable when valid audio
callbacks stop, including if the UI task remains alive. Software bypass and
power-failure bypass are separate behaviors.

The [E01 electronics design basis](../../../research/hardware/audio-design-history.md) calculates both line
gain ranges and power/headroom constraints. Its draft uses separate input
isolation and output selector relays, two gain relays, and an edge-armed watchdog
latch. These are circuit contracts pending a complete schematic, not assembled
electronics. The rear CONNECTION switch selects gain independently of wet/dry
routing.

The [E02 native watchdog/driver schematic](../../../hardware/electronics/bypass/README.md) now
includes local 3.3 V/5 V supervision, Schmitt qualification, manual process-loop
continuity, an edge-armed latch and two coil drivers. Firmware monitors latch Q
on D28. Native ERC and 25 ideal fault cases pass; six host suites pass and the
embedded application cross-compiles. Analog-rail monitoring, PCB layout and
physical bypass/audio performance remain unfinished.

The [E03 stereo contact schematic](../../../hardware/electronics/audio_bypass/README.md) now
connects the two bypass relays to that driver. It passes native ERC, checks all
four settled relay combinations and matches the E02 coil interface. The relay
land pattern also matches the manufacturer's nominal drawing. The contacts,
analog stages and power circuits still need an integrated PCB and bench tests.

The [E05 native output stage](../../../hardware/electronics/output_stage/README.md) adds separate
master/send-return drivers, coupling/discharge networks and the output gain
relay. Native ERC, 12 ideal AC cases, four ideal DC cases and 256 component
tolerance cases pass. The converter/receiver, input range and supplies remain
unfinished. All four proposed analog rails need independent supervision.

The [A03/E07 output board](../../../hardware/electronics/output_stage/generated/routing-verification.json)
puts all 41 output footprints into the revised enclosure with staggered
capacitors, a lower board and a floor recess. Modeled component/lead clearances
and the seven enclosure solids pass. The output board is routed and its saved
AGND plane is filled: native DRC/library/parity checks pass with zero violations
and zero open connections. Physical fit, final stackup/parts, audio performance
and the remaining converter/input/power placement are not complete.

The [E08 DAC I/V and receiver schematic](../../../hardware/electronics/dac_receiver/README.md)
now connects the prospective DAC boundary to that output interface. Native ERC,
exact pins, loaded ideal AC/DC and passive corner checks pass. It adds DC blocking
and a low-bias buffer, and identifies a one-second analog/codec settling
requirement. Raw DAC scale, gain calibration, fault protection, converter
power/clock/configuration, complete noise closure and PCB placement remain open.
The [E08 review bundle](../../../hardware/releases/README.md#standalone-review-e08) includes this
new circuit and the existing A03/E07 CAD and routed output board.

The [E09 converter core](../../../hardware/electronics/converter/README.md) now adds the codec pin
connections, local 3.3 V/4.5 V analog supplies, a synchronous 24.576 MHz clock and
hardware reset/settling qualification. Its native ERC, 49-pin codec contract and
256 powered logic cases pass; timer bounds conditionally exceed E08's one-second
requirement. The codec footprint awaits its manufacturer drawing, and the new
E09 JSON retains the historical pin proposal; F01 implements its matching adapter. E08/E09 have no
PCB/enclosure placement. The [E09 review bundle](../../../hardware/releases/README.md#standalone-review-e09)
contains the E09 hardware snapshot without changing the earlier CAD scope.

The [F01 external-converter firmware](../../../hardware/firmware/EXTERNAL-CONVERTER.md) now
implements the separate pin profile, codec configuration/readback, silent SAI2
startup and hardware-qualification gating. Both ARM profiles build and seven
host suites pass, including delayed settling, clock/ramp faults and relay-policy
interaction. F01 is later than the E09 archive. The new rear/status PCB, actual
clock/DMA timing, converter audio performance and complete internal placement
still require implementation or physical validation.

The [E10 input-range preamplifier](../../../hardware/electronics/input_range/README.md) now adds
the stereo gain relay, loaded passive master attenuation, input AC coupling and
low-voltage FET buffer. Its 28-component native schematic passes ERC, 24 loaded
AC comparisons, 64 allocated DC cases and 1,024 mode/tolerance cases. It ends at
a single-ended preamplifier boundary; the ADC driver/bias/protection remains
unfinished. E10 also identifies a required independent input precharge interval:
E02/E03 currently energize input isolation and wet output together, and F01 does
not implement that input-settling sequence. This historical E10 conflict is now
addressed by the E11 schematic and F02 firmware below. E10 has no PCB or CAD placement.
The [E10 design review package](../../../hardware/releases/README.md#standalone-review-e10) includes
the current project sources and the earlier CAD/F01 work. It is not a build or
fabrication release.

The [E11 independent relay sequencer](../../../hardware/electronics/sequenced_bypass/README.md)
now drives the processing-input relay separately, holds wet output dry through
an approximately two-second hardware timer, and requires a fresh permit edge.
Gain changes and health loss restart qualification. Manual bypass keeps a
healthy input connected. F02 adds INPUT_READY on MCP0x22 GPA3, 1.25 seconds of
continuous software quiet and the existing350ms stable rearm; unsettled ADC data
is masked before reaching DSP histories. Native ERC,55 exact pin/value contracts,
256 powered logic cases,seven fault sequences and both ARM/eight host checks pass.
Timer startup, RC thresholds, component/relay timing allocations and physical
bypass/audio still need validation. E11 has no PCB or CAD placement.

## Memory evidence

`rmx_hardware_profile` measures C++ heap payload for the actual engine and factory
sample bank on the development host. It also exercises the processing path and
reports any allocations during that interval. It does not measure MCU allocator
overhead, firmware code, stacks, DMA buffers, or processor timing.

```sh
cmake -S . -B build-hardware -DCMAKE_BUILD_TYPE=Release
cmake --build build-hardware --target rmx_hardware_profile --parallel 4
./build-hardware/rmx_hardware_profile 48000
./build-hardware/rmx_hardware_profile 96000
```

At 48 kHz the current engine allocates 26,433,392 bytes of buffers; the factory
bank adds 2,396,160 bytes. A proposed 32-second **aggregate** stereo sample limit
would bring engine + sample payload to 38,721,392 bytes, below a 48 MiB heap
reservation. This is an initial capacity constraint, not an implemented sample
loader limit. Bank replacement must not transiently retain a second full bank.

At 96 kHz, engine + that sample limit would require 77,442,112 bytes, so it is
rejected for this 64 MB module. Preserve the desktop's existing rates; the
standalone adapter will explicitly support 48 kHz until a different memory
configuration and on-device profiling justify more.

## Mechanical work

See [CAD and control layout](2026-10-23-cad-design.md). Preserve the RMX-style control
arrangement while adding the internal audio/power carrier, panel control boards,
release mechanism, optical parts, and rear I/O. Reserve the independent bypass
path and service access as part of the layout.

The [component shortlist](../../../research/hardware/components.md) records the current controls, sensor,
display and driver choices. The [embedded prototype](../../../hardware/firmware/README.md) now
builds for Seed3 with local audio processing, control input and feedback. It has
not been flashed or tested on a physical board.

## Required completion gates

- [x] Standalone operation is the selected architecture.
- [x] First housing and control layout exists.
- [x] Actual C++ buffer allocations measured; initial 48 kHz memory budget fits.
- [ ] Component selection and manufacturer dimension checks completed.
- [x] A02 CAD contains component reserves, PCB supports, rear I/O and lever motion.
- [x] Seven CAD solids rendered, mesh checked, and fit coupon exported.
- [x] Embedded engine adapter cross-compiles with the pinned board support package.
- [x] Front control logic, feedback serialization and SDRAM arena have host checks.
- [ ] Control/sensor/LED drivers and calibration bench tested on the actual board.
- [ ] Audio gain stages, bypass, watchdog and power schematics reviewed.
- [ ] Carrier and control PCBs routed and checked.
- [ ] Physical control coupon assembled and hand spacing reviewed.
- [ ] Full prototype assembled and runs with no computer connected.
- [ ] Worst-case MCU timing, round-trip latency, power-failure bypass, noise,
      distortion, headroom, thermal and two-hour soak tests measured.

The remaining physical gates require the actual parts and test equipment. CAD
clearance checks and host tests cannot substitute for those measurements.

The [B01 button fit kit](../../../hardware/cad/BUTTON-FIT.md) now includes two key sizes, three
guide-clearance options, a retaining clip and a routed passive test PCB with
zero native KiCad ERC/DRC/parity issues. Its eight hard parts pass mesh and rigid
motion checks. This is a separate prototype fixture; the full control PCBs and
production button installation remain open, along with spring/contact selection
and the actual fit/force/closure test.
