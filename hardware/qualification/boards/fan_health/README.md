# FH01 fan-health firmware candidate

The firmware record below is retained alongside the later sealed FH02 circuit
and [FPC01-M1 fan PCB](composite_mount/README.md). FPC01-M1 contains84 parts and
passes strict native ERC, DRC, connectivity and schematic parity checks, with
six mounting/copper regression tests. It adds actual all-layer clip keepouts
and preserves the original component geometry. The independent review of the
original FPC01 is recorded in
[review.json](../../../cad/a12/qualification_reviews/fpc01/review.json).
Native circuit/layout completion does not establish installed fault response,
cooling, mounting material or physical qualification. The paragraphs describing
unimplemented hardware below document the earlier FH01 firmware stage.

This is a **software candidate**, not a qualified fan controller or a build-ready
board. The portable C monitor has host fault-injection tests and compiles for the
ATtiny84 instruction set. No microcontroller has been programmed or exercised.
The current run passes 12,647 assertions and uses 1,760 bytes of code plus
90 bytes of static RAM; these figures exclude worst-case stack qualification.
`generated/verification.json` records source hashes, exact build commands, compiler
archive checksum, logs, memory sizes and explicit unresolved qualification flags.

The proposed hardware is an ATtiny84A-SSUR with an external 4 MHz crystal and
full-speed core. The raw 500 kHz timer is extended before division to 125 kHz
engine timestamps, preserving full rollover behavior. A separate TPS3431 must
supervise a heartbeat generated after each complete main-loop measurement. Its
fault output must independently override the MCU permission output. Neither the
external watchdog nor the proposed output circuit is implemented in a native
schematic in this folder yet.

The intended output interrupts only the P03 J106.3 POWER_RUN branch to E28 J5.3.
The raw fan supply remains available during startup. E28 MASTER_ENABLE is an
internally driven signal and must not be driven by this controller. The proposed
normally open TLP175A output, partial-power behavior, leakage, output discharge and
entire wire path still require a native design and verification.

The monitor requires both fans to deliver eight consecutive acceptable periods,
then remain healthy for 500 ms. It times out after five seconds during startup.
During operation, missing pulses, bad speed, sensor faults, high temperature,
capture loss and late monitor cycles latch the output off. Watchdog, brownout or
external reset without a clean power-on reset also latch it off. A clean power
cycle is the intended reset; this behavior has not been tested on silicon.
An entry through the reset vector with no hardware reset flags is also unsafe;
it cannot authorize a new startup cycle.

Period limits are 375–680 ticks (nominally about 10,000–5,515 rpm for two pulses per
revolution). These are software limits, not an airflow guarantee. The complete
clock error and interrupt capture error remain receiving requirements. The ADC
trips at or below 186 counts, treats 0–8 as shorted and 1000–1023 as open, on either
sensor. The complete period-measurement receiving target is ±20 engine ticks;
it has not been verified on silicon. The faster core and separate tick/channel
queue arrays reduce interrupt latency without costly five-byte array indexing.
The proposed sensor is SEMITEC 203AT-2 with a 20 kΩ pull-up. Its actual R/T
curve, ADC error, leakage, filter, placement, thermal lag and complete hot trip
interval must be qualified before assigning a guaranteed temperature limit.

Target pin allocation:

| Signal | Port | SOIC pin |
| --- | --- | --- |
| Temperature 1 / 2 | PA0 / PA1 | 13 / 12 |
| Software heartbeat | PA2 | 11 |
| Fan left / right tach | PA3 / PB2 | 10 / 5 |
| MCU permission | PA7 | 6 |
| ISP SCK / MISO / MOSI | PA4 / PA5 / PA6 | 9 / 8 / 7 |
| Reset | PB3 | 4 |
| Crystal | PB0 / PB1 | 2 / 3 |
| VCC / ground | — | 1 / 14 |

The adapter checks low/high fuse values `0x7d` / `0xdd` before permitting operation.
These values are a proposed programming contract; no programming command is run
by this repository script. External crystal selection, oscillator startup, fuse
readback, brownout behavior and programmer isolation are still open.

Reproduce the current macOS build with the official Arduino AVR GCC
7.3.0-atmel3.6.1-arduino7 toolchain and Clang:

```sh
python3 hardware/qualification/boards/fan_health/verify_firmware.py \
  --avr-bin /path/to/avr-gcc/bin \
  --compiler-archive /path/to/avr-gcc-7.3.0-atmel3.6.1-arduino7-x86_64-apple-darwin14.tar.bz2
```

The script checks the archive against the official Arduino package-index SHA-256,
rereads every installed toolchain file against that archive,
runs host tests with address/undefined-behavior sanitizers, compiles actual AVR
objects, and emits ELF, HEX, map, disassembly and normal-function/ISR stack-usage
files. GCC cannot compute stack use for the isolated naked startup function;
the rejected attempt before separating that function
is retained in `generated/rejected_adapter_stack_usage.log`. The SRAM size
check covers static data only. Worst-case call/interrupt stack use, adapter timing,
ADC settling, timer rollover, queue races, watchdog behavior, electrical fault
injection, PCB layout, installation and whole-unit thermal qualification remain
unverified. A successful build is not permission to manufacture or operate it.

`temperature.py` records a conditional 128-corner beta/ADC comparison for the
proposed 203AT-2, 20 kΩ pull-up and 1 kΩ series filter. It predicts about
60.87–64.27°C trip temperatures under the stated receiving assumptions, while
the guaranteed trip interval remains null. The actual R/T curve, ADC error and
sensor placement/lag are not qualified. The portable CI suite exercises this
comparison alongside the actual C monitor and parallel-branch airflow tests.

The later [RT01 supplier-table review](rt_curve_review/README.md) captures a
public SEMITEC nominal R/T table and compares its interpolation with this beta
model. Its conditional trip interval is61.30–64.67°C. Sparse nominal points do
not qualify local R/T tolerance, interpolation error, ADC error or installed
thermal lag; the guaranteed shutdown interval remains unassigned. The sealed
FH02 and firmware threshold are unchanged.
