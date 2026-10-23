# F04 standalone external-converter firmware

F04 corrects the MCP23017 front-input map and verifies expander configuration.
It retains F03's bounded power-up probing for the E13 rail monitor, the E09
ES9292QPRO adapter and F02's E11 input qualification. Both the onboard-codec
and external-codec builds cross-compile. Nine
host suites check the engine and control/qualification policies. Neither build
has been flashed or run on hardware. Converter scale, clock phase, analog audio
performance and complete electronics placement remain unverified.

```sh
make -C hardware/firmware PROFILE=external GCC_PATH=/path/to/arm-toolchain/bin
make -C hardware/firmware PROFILE=onboard GCC_PATH=/path/to/arm-toolchain/bin
python3 hardware/firmware/verify.py --toolchain /path/to/arm-toolchain/bin
```

External output is `build-external/rmx_standalone_external.{elf,hex,bin}`;
onboard output remains `build/rmx_standalone.{elf,hex,bin}`. Object directories
are separate and unknown profiles are rejected. The verifier checks the pinned
SDK, both ARM builds, nine host suites, actual ELF sections/DMA placement and
source hashes. See [its record](../validation/external-firmware.json) and the
[main guide](README.md) for bootloader, calibration partitions and linker warnings.

## Matching wiring

Use the E09 [SAI pin plan](../electronics/converter/interface-plan.json) with the
[E11 relay/status interface](../electronics/sequenced_bypass/integration.json):

| Seed pin | F04 external profile |
| --- | --- |
| D0 / PB12 | CODEC_RUN and active-low reset of all three MCP23017s |
| D25 / PA0 | SAI2B ADC_DATA receive, AF10 |
| D26 / PD11 | SAI2A DAC_DATA transmit, AF10 |
| D27 / PG9 | External WS into SAI2B, AF10 |
| D28 / PA2 | External BCLK into SAI2B, AF8 |
| D29 / PB14 | Direct MCU_PERMIT to E11 J2.3 |
| D30 / PB15 | Latch-Q feedback from E11 J2.5 |

The third MCP23017 at seven-bit 0x22 reads active-low connection mode on GPA0,
active-low bypass sense on GPA1, active-high ANALOG_OK on GPA2 and active-high
INPUT_READY on GPA3. GPA2/GPA3 have no internal pull-up and require physical
receiving-end pull-downs: **47 kΩ for ANALOG_OK and 270 kΩ for INPUT_READY**.
The larger INPUT_READY resistor preserves the HCS gate's static output-level
budget. These receiving pull-downs are now on the routed
[E18 input hub](../electronics/control_inputs/README.md). Complete control PCBs
and physical status-harness qualification remain unfinished. Other
LEDs and SDMMC reservations retain their assignments. No MCU MCLK pin
is used. The E09 JSON remains the historical proposal; the matching executable
profile is recorded in [external-profile.json](external-profile.json).

Both profiles now require all three MCP23017s for the front controls. Inputs
0-13 use 0x20 GPA0..6/GPB0..6; inputs14-27 use the same pins on0x21;
inputs28-31 use0x22 GPB0..3. These last four are Scene9, Default/User,
Back Spin and Vinyl Brake. GPA7/GPB7 are output-only in Microchip's
[current specification](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf)
and are left unconnected. The older two-expander front wiring is incompatible.
The [F04 map](control-inputs.json) includes SOIC pin numbers and panel centers.
E18 implements the digital-input connections and a100k receiving reset pull-down;
J4 rear/status must be unplugged for onboard-profile bring-up.
Rear/status GPA0..3 stay fixed and do not enter the front button frame.
Direction/pull-up/latch readback failures stop initialization; any failed scan
returns no new frame and removes normal processing eligibility. The third read
adds bus traffic; actual control latency and I²C integrity remain unmeasured.

The codec is master: 24.576 MHz ACLK1, MCLK/8 BCLK and two 32-bit I2S slots at 48 kHz.
MCU SAI2B receives external clocks/data; A transmits synchronized to B. The pinned
SDK marks 32-bit mode untested. ESS's default I2S master phase is retained
(register 9 = 0x25, preserving reserved bits). Edge phase, channel alignment and
clock integrity require scope and audio-loop measurements.

## Startup, monitoring and faults

`BoardIO` holds D0 low for at least 20 ms, releasing expanders and codec run request
together. **E09 hardware** gates CHIP_EN with CODEC_PGOOD and PRE_ANALOG_OK;
those rails have no separate MCU status inputs here. E13 adds independent rail
windows and a coarse startup guard with a 180–420 ms release interval. Main supply
generation is still unfinished, and actual startup timing is unmeasured.

`ConverterPower.h` probes chip ID every 5 ms before configuration. A NACK during
this phase restarts the observed response interval; ID 0xAF must respond over
20 ms before setup begins. A responding wrong ID faults immediately. Missing or
chattering responses cannot extend the five-second deadline. The deadline and
polling work across the millisecond timer wrap. Audio callbacks, heartbeat and
relay permit have not started, so the output remains in dry bypass. This adds no
GPIO. The 20 ms interval is a software qualification choice, not a manufacturer
startup-time guarantee. Supply and reference startup must be measured.

After this phase, every configuration/readback or runtime bus failure retains
the existing latched fault behavior. Failed startup leaves dry bypass and
requires restart after repair.

`Es9292.h` uses seven-bit address 0x18 and checks ID 0xAF at register 225. It disables
qualification outputs and mutes DAC/direct monitor before configuration. Each
setting preserves reserved bits with read-modify-write and full-value readback.
Paired registers are read/written LSB first and checked after their MSB commits.

Setup explicitly selects stereo 32-bit I2S, L/R slots 0/1, fixed MCLK/4 128fs
division, 24.576 MHz backend, clock monitors, unity digital gain and built-in
minimum-phase filters. ADC DC blockers remain enabled; internal ASPs are
disabled/bypassed. Direct monitoring stays muted and at minimum volume so audio
passes through the MCU engine. This recipe needs manufacturer/hardware validation.

After four callbacks on zero-filled DMA, the DAC unmutes while DSP output stays
digitally silent, then GPIO3 clock-valid/GPIO4 both-channel ramp-done outputs are
enabled. Automute and mute-to-ground are disabled to retain DC bias during
silence or ordinary digital muting. The resulting current/thermal cost needs
measurement.

The GPIO ramp-done flag can also be high while the DAC is fully ramped down.
F01 additionally requires both **ramped-up** live bits, no ramp-down/automute/
minimum-volume flags, valid PCM encoder/decoder and valid clock ratios. It waits
at least 1,211 ms of continuously valid streaming/clock/ramp state and requires
external ANALOG_OK. E09 independently provides its conditional 1.21–4.52 s timer.
Interrupted streaming/clock/ramp restarts the software quiet interval; missing
qualification times out after 8 s. Expected settling does not emit a premature
relay-permit edge or trip the 20 ms latch-feedback timeout.

The [E11 sequencer](../electronics/sequenced_bypass/README.md) independently closes
the processing-input relay on healthy power/watchdog/analog status and holds
the output in dry bypass during its approximately two-second input timer. Both
gain edges restart that timer. `InputQualification.h` then requires INPUT_READY
high for **1,250 continuous ms** before processing is eligible. Low status drops
permit immediately and restarts the quiet interval; missing/chattering readiness
for 10 seconds latches a fault. Loss after a long ready period gets a fresh
recovery deadline. A missing status bus always faults. The external DMA callback
continues with digital silence while input settling is expected. Unqualified ADC
samples are replaced with zero before reaching DSP delay/roll histories; input
acceptance is revoked before writing a changed gain drive.

Manual bypass clears the output latch but keeps the input relay connected while
hardware health is valid. Input qualification stays warm, and manual release
still needs the existing 350 ms stable rearm and a fresh permit edge. Gain
transitions and calibration restarts reset the software input interval even if
the sampled INPUT_READY value is still high. Startup waits for both converter
and input qualification before attempting to arm. The display shows `In` during
expected input settling, subject to calibration/error display priority.

Then calibration, manual bypass, gain sequencing, audio warmup, fresh controls
and 350 ms stable rearm can request processed output. Codec status is checked every 4 ms;
one configured register group is audited on each poll. Observed bus, status,
configuration, audio-stall or qualifier loss latches a fault and removes permit.
E11/E09's physical watchdog/qualification remains independent of software polling.

Calibration storage pauses DMA while retaining codec clocks/DC bias. Restart
requires new silent callbacks and fresh converter/input quiet intervals without
rewriting analog settings. Other codec reconfiguration requires reboot through
the complete reset/setup sequence.

## Audio transport and evidence limits

`ExternalAudio.cpp` uses raw SAI DMA because the pinned `AudioHandle::Start`
discards DMA-start errors. A partial start failure stops both blocks and faults.
RX/TX buffers are 32-byte aligned in uncached D2 SRAM. PCM conversions handle
signed 32-bit scale, nonfinite values and saturated endpoints.

The callback stages a complete output half, then checks the pinned SDK's SAI2A
TX DMA stream 3 counter before copying. It rejects an active/late half. The
provisional 16-word guard is about 166 µs at 48 kHz; copy/callback maxima are recorded
and copies above 80 µs or callbacks above 2400 µs fault. These are **not measured
deadline or phase proof**. Actual RX/TX phase, copy margin and interrupt behavior
need bench verification. DMA errors and observed SAI frame/under/overrun flags
also fault.

Host checks cover 312 injected setup/activation/configuration failures, reserved
bits, paired-register latching, ramp-up versus ramp-down, delayed/interrupted
settling, timeouts/wrap, calibration restart, stalled audio, the actual relay
policies and PCM/DMA boundaries. The eighth suite adds input timeout/chatter,
stale status, calibration, manual bypass, gain changes and power recovery using
the actual input/gain/rearm/feedback policies, also across timer wrap.
The register model does not emulate converter
or STM32 peripherals, bus electrical timing or analog transients.

Complete the ADC/input circuit, power converters/rail monitors, package drawing,
carrier/control PCBs and E08/E09 placement. Original noise/headroom targets,
gain calibration, storage, latency, bypass transitions, thermal and two-hour
soak gates remain open.

Primary source: [ESS ES9292PRO v0.1](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf),
register ordering and registers 0–17,61–84,89–92,105–120,136–148,218–241.
SDK source evidence is pinned and hashed in the verification record.
