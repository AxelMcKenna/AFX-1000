# Standalone embedded prototype

The separate [F06 maintained-engine candidate](full_engine/README.md) builds the current 152-parameter DSP with exact kernel restoration, bounded SDRAM storage and control-fault recovery. The instructions below describe the preserved F05 runtime build. Neither build has been run or qualified on physical hardware.

This application builds the existing RMX engine for Daisy Seed3. Audio processing,
factory samples, tempo detection, front controls and feedback run on the module;
no Mac, USB host or network connection is required for operation. It has been
cross-compiled, **not run on a physical board**. Analog circuitry, power, bypass
hardware, assembled controls and on-device validation remain required.

The default build uses the onboard codec for bring-up. The
[E04 noise screen](../../research/hardware/audio-design-history.md#e04-converter-gain-and-noise-screen)
does not approve that converter for the final reference-performance design.
The [F04 external-converter profile](EXTERNAL-CONVERTER.md) implements a
separate ES9292QPRO/SAI2 adapter with configuration/readback, silent startup and
hardware-qualification gating. Both profiles cross-compile; neither has run on
hardware. Preserve the wiring contract below for the default onboard build.
Use the matching F04/E11 pin plan for `PROFILE=external`. The external profile waits
for independent input settling, masks unsettled ADC data before DSP histories
and keeps input qualification warm during ordinary manual bypass. Both ARM
profiles and all nine host suites pass; physical timing/audio remain unverified.

**F04 changes the control wiring for both profiles.** Microchip's
[DS20001952D](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf)
lists GPA7/GPB7 as output-only on MCP23017. The earlier two-chip 32-input map
is incompatible with that specification. Both profiles now require **three**
expanders at 0x20/0x21/0x22. Use the generated [pin map](control-inputs.json)
or [wiring CSV](control-inputs.csv); the logical control order is retained.
The [E18 input hub](../electronics/control_inputs/README.md) now implements these
digital inputs on a routed daughterboard; the complete control PCB is unfinished.

The standalone build uses the isolated [firmware runtime](../runtime/README.md) in `hardware/runtime/`. The root desktop engine and the older B1 firmware adapter retain their own implementation and build paths.

## What is implemented

- Fixed stereo 48 kHz / 128-frame audio callback, with preallocated factory bank.
- 48 MiB SDRAM arena for large vectors; bounded metadata in internal SRAM.
- Ten ADC pots, three MCP23017 input expanders, Trill Craft touch acquisition,
  AS5600 release sensing, and a four-chip TLC5947 LED/display chain.
- Verified expander direction, pull-up and output-latch configuration. Unused
  outputs stay low; failed configuration/readback stops startup. Button scans
  publish all 32 inputs only after all three reads succeed.
- Front control behavior shared with host-tested `HardwareControls.h`.
- Two-endpoint lever calibration with two alternating CRC-checked QSPI records.
- Audio-callback heartbeat and relay permit. Permit requires fresh controls,
  valid calibration, healthy startup and no latched processing fault.
- Dry-bypass request if I/O fails or the foreground loop stalls. Processing
  resumes only after healthy inputs remain stable for 350 ms. Callback overruns
  above 2400 us or nonfinite samples latch a fault until restart.
- Rear CONNECTION selects analog gain through a sequenced driver: immediate dry
  bypass, 8 ms debounce, 20 ms dry wait, gain change, 30 ms settling, then the
  existing healthy rearm interval. It does not enable wet-only DSP routing.
- E02 latch feedback on D28: allow 20 ms for initial arming, remove permit on
  lost feedback, and latch a fault if loss persists for 20 ms. The manual-switch
  poles may arrive at different times within that allowance.
- A fresh 350 ms continuous eligibility interval follows manual bypass,
  calibration, gain settling, input faults and the initial 128-block audio
  warm-up. It prevents a premature latch clock on manual bypass release.

These are software behaviors, not proof that the proposed circuits satisfy them.
The external watchdog, relay gating and normally closed bypass must be built and
measured independently. The DAC float output is clamped to [-1,1]; that does not
establish analog headroom or a matching gain range.

## Build

Use the exact SDK revision in `dependencies.json`, including its recursive
submodules. Keep it outside the firmware source directory:

```sh
git clone https://github.com/daisyaudio/libDaisy.git build-hardware/libDaisy
git -C build-hardware/libDaisy checkout f715e4875b2d28445d0c11a0a17f064a248f69d0
git -C build-hardware/libDaisy submodule update --init --recursive
make -C build-hardware/libDaisy -j4 GCC_PATH=/path/to/arm-toolchain/bin
make -C hardware/firmware PROFILE=onboard -j4 GCC_PATH=/path/to/arm-toolchain/bin
make -C hardware/firmware PROFILE=external -j4 GCC_PATH=/path/to/arm-toolchain/bin
```

`LIBDAISY_DIR` can override the default `../../build-hardware/libDaisy` when invoking
make from `hardware/firmware`. Arm GNU Toolchain 15.3.Rel2 was checked. C++20 is
required. The application uses `BOOT_SRAM`, not the 128 KiB internal-flash layout.
Install the matching Daisy bootloader on the actual Seed3 before programming the
application through its DFU workflow. No hardware was programmed in this work.

Build products are `build/rmx_standalone.bin`, `.elf`, `.hex` and `.map`. The
application reserves QSPI offsets `0x007f0000` and `0x007f1000` for calibration.
Keep firmware, assets and any future storage partition clear of those sectors.
The records do not depend on native filesystem/syscall support.

The pinned SDK/newlib link emits warnings for unsupported host POSIX syscalls
and the SDK SRAM linker segment's RWX permissions. No POSIX file or terminal I/O
is used by this application. The [F05 boot-storage extension](STORAGE.md) uses the embedded FatFs adapter for
optional samples, boot presets and the six user settings. It is read-only and
finishes before audio starts; SD hardware and timing remain unqualified. The linker map and actual hardware remain the authority for
memory use and timing.

## Wiring contract

All logic and I2C pull-ups are 3.3 V. Keep analog pot excitation/returns on the
module's analog supply/ground domain, with the manufacturer's required AGND/DGND
connection. Do not power the processor from the logic output pins.

| Seed logical pin | Function |
| --- | --- |
| D0 | Hardware bypass sense, active low; switch also directly gates relay enable |
| D1-D6 | F05 boot-only SDMMC storage; socket/detect wiring and power remain unqualified |
| D7 | TLC5947 XLAT |
| D8 | SPI1 clock for TLC5947 |
| D9 | Gain relay driver request; low Master / high Send-Return; external pull-down |
| D10 | SPI1 MOSI to TLC5947 IC0 SIN; chain SOUT to the next IC |
| D11 / D12 | I2C1 SCL / SDA at 400 kHz |
| D13 | Audio-callback heartbeat to independent watchdog |
| D14 | TLC5947 BLANK; external pull-up keeps lamps off during reset |
| D15-D24 | Input, Output, Low, Mid, Hi, Scene Depth, X Level, Pitch, Sub1, Sub2 pots |
| D25 | Master/send-return mode sense, active low for send-return |
| D26 | Processing relay permit; external pull-down and watchdog/bypass gating required |
| D27 | Onboard-profile shared MCP23017 RESET, active low; E18 receiving100k pull-down |
| D28 | E02 latch-Q feedback, active high; MCU pull-down makes a missing connection low |
| D29 / D30 | Reserved; do not connect the panel USB cable here in this prototype |

The [E09 external-converter interface plan](../electronics/converter/interface-plan.json)
is the basis of the separate external profile: D25–D28 become dual-slave SAI2, D29 permit,
D30 latch feedback and D0 codec-run/shared MCP reset. The third MCP23017 reads
four front inputs on GPB0..3 and, in the external profile, rear controls,
ANALOG_OK and E11 INPUT_READY on GPA0..3. F04 implements that adapter as
`PROFILE=external`; the table above describes `PROFILE=onboard`. It first uses
bounded chip-ID probing while the E13 rail guard holds the codec disabled. It then waits for
hardware ANALOG_OK, continuous streaming/clock/ramp-up qualification and the
independent input sequence before a permit edge. GPA2 ANALOG_OK needs47kΩ and
GPA3 INPUT_READY needs270kΩ receiving pull-downs, now present on E18;
both internal pull-ups are disabled. E11 replaces E02/E03 for this profile.

The service connector uses a short USB extension to the module's own USB-C port.
Supply voltage and polarity are not finalized until the analog/power schematic
is reviewed. Power switching, line gain switching and relay-coil drive are not
implemented by connecting a GPIO directly to a coil or analog audio signal.

The [E02 watchdog/driver schematic](../electronics/bypass/README.md) drives two DPDT gain relays
controlled by D9 through a MOSFET driver, independently of the two bypass relays.
`ConnectionMode.h` guards gain transitions while dry bypass is requested. Normal
standalone routing retains the dry signal; wet-only needs a separate future
setting for parallel auxiliary buses. Actual coil timing and contact bounce must
be measured before accepting the prototype intervals.

The bypass watchdog requires a hardware fault latch: WDO can recover after its
reset interval even with D26 frozen high. The proposed edge-armed latch stays
disarmed until a new D26 rising edge. This circuit remains a design draft; the
firmware's GPIO behavior cannot supply that independent protection by itself.

E02 manual bypass uses a closed PROCESS_OK contact loop as well as the separate
active-low D0 sense pole; an open process-loop cable inhibits hardware enable.
Its J2.5 routes latch Q to D28. Missing feedback prevents a successful arm attempt
and results in a latched fault. D28 senses the logic latch, not relay contacts.
Full analog-rail supervision and actual circuit testing remain mandatory gates.

| I2C device | 7-bit address | Use |
| --- | --- | --- |
| MCP23017 #0 | 0x20 | Inputs 0-13 on GPA0..6, then GPB0..6; address straps all low |
| MCP23017 #1 | 0x21 | Inputs 14-27 on GPA0..6, then GPB0..6; A0 high, A1/A2 low |
| MCP23017 #2 | 0x22 | Inputs 28-31 on GPB0..3; rear/status GPA0..3 in external profile; A1 high, A0/A2 low |
| Trill Craft | 0x30 | Electrodes 0-7; other channels remain unused |
| AS5600 | 0x36 | Status and raw angle |

Each front input is active low. Use GPIOA bits 0-6 before GPIOB bits 0-6 on
the first two chips; **never use GPA7 or GPB7 as an input**. Inputs 0-28
follow `buttonIds` in `HardwareControls.h`; input 29 is
Default/User, input 30 Back Spin, input 31 Vinyl Brake. Neither release end input
means Echo; both asserted is a wiring/state error. Configure the mode switch so
it cannot short both end contacts simultaneously.

The onboard profile also needs the third chip for inputs28-31; its GPA0..3
are unused outputs because rear sensing uses MCU pins. All unused GPIOs are
unconnected and configured as low outputs. The shared RESET must physically
reach all three devices before configuration. E18 adds a100kΩ receiving reset
pull-down. Use no additional reset pull-up: the external profile shares the
line with CODEC_RUN, which must default low. `ControlExpanders.h` writes OLAT
before IODIR, applies pull-ups only to valid active-low inputs, then reads back
OLAT/IODIR/GPPU. Physical scan latency, bus capacitance/rise time, harness noise
and operation at reset still need measurement. Regenerate the wiring files with
`python3 hardware/firmware/control_map.py`; `--check` checks freshness.

Trill uses DIFF mode, ultra-fast 10-bit scans, prescaler 2, and a baseline update
at startup. Eight electrodes feed a centroid around the strongest touch. The
threshold is a prototype constant in `WireFormat.h`, not a calibrated production
setting. Finger-off startup, cover thickness, noise rejection and latency must
be tested. Protocol reference: [Bela's Trill-Arduino source](https://github.com/BelaPlatform/Trill-Arduino),
with scan behavior described in the [manufacturer's settings guide](https://learn.bela.io/using-trill/settings-and-sensitivity/).

## LED/display channel contract

Global channel `n` maps to IC `n/24`, output `n%24`. IC0 is nearest the MCU.
`WireFormat.h` sends the furthest/highest channel first, MSB first.

| Channels | Indication |
| --- | --- |
| 0-9 | Scene selections in engine order |
| 10-13 | Isolator mode |
| 14-15 | Input / sampler source |
| 16-19 | Pad trigger flashes |
| 20-24 | Quantize, Auto, Roll, Overdub, Hold |
| 25-44 / 45-64 | Input / output meters |
| 65-68 | Sample bank |
| 69-92 | Three digits, eight channels each, a/b/c/d/e/f/g/decimal point |
| 93-95 | Ring R/G/B |

Current limits are hardware-set; PWM brightness is not a current limiter. Use
common-anode display parts and the TLC5947 manufacturer's required current-set,
decoupling and thermal design. Default/User currently changes the shared flag;
F05 [boot storage](STORAGE.md) loads those six settings and a bounded boot preset; runtime writing/reloading remains open.

The [E20 driver core](../electronics/led_driver/README.md) implements the four-chip
chain, 3.3-to-5 V translation and supervised BLANK gating. `BoardIO.h` supplies
explicit 1 µs latch guards; startup and SPI failure hold BLANK high. Frames update
every 33 ms. Host wire tests walk all 1,152 PWM bits through an independent
four-register cascade model. Native PCB checks and host tests do not establish
physical signal timing, brightness, partial-power recovery or optics. E20 also
exposes an unclosed system power allocation; its panel emitters and harnesses
remain unfinished.

## Prototype calibration and first-power procedure

First establish power, grounded analog I/O and normally closed dry bypass with
the processor disabled. Confirm the relay cannot engage when the watchdog is
missing/stopped. Measure the actual analog levels before connecting a mixer.

An uncalibrated unit stays in dry bypass and shows `CAL`. With the rear hardware
bypass selected and the lever released, hold **Bank + Tap for two seconds** to
capture home. Release those buttons; the display shows `End`. Pull to the
mechanical end stop and hold Bank + Tap for two seconds again. Audio pauses while
the new CRC record is written/read back. Both rotation directions and encoder
wrap are supported. Invalid travel is rejected and the unit remains bypassed.

This requires the assembled lever and sensor. Physical stops, magnet field,
spring return, bearings and actual travel must be checked before accepting that
calibration. Do not calibrate against an unsupported or forced lever position.

## Remaining bring-up gates

- Measure worst-case callback time on Seed3 with all effects, pad voices, rolls,
  input scanning and LED traffic active; host timing is not this evidence.
- Validate both channels, unity gain, clipping, send/return routing, converter
  noise/distortion and physical round-trip latency.
- Build the external watchdog/bypass and verify boot, MCU halt, I/O fault,
  brownout, power loss and reset behavior with an audio signal.
- Physically validate the F05 SD socket, card power/inrush, DMA/cache transfers,
  boot-time bounds and factory fallback. Runtime writing/reloading remains open.
- Add calibration/preset recovery tests, measured ADC endpoints and physical
  control/LED tests. No claim of a two-hour hardware soak is made.
