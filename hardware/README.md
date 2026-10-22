# RMX hardware prototype A0

This is the first physical implementation path toward the full clone. It is a development design, not a fabrication release or an assertion of measured RMX sound. The current deliverables are a common control/pin manifest, generated panel DXF/SVG, an editable OpenSCAD enclosure, a preliminary BOM, and a Daisy firmware adapter for the shared engine.

## Mechanical files

- `prototype.json` is the source for dimensions, cutouts, control channels, rear ports and GPIO assignments.
- `generated/panel.svg` and `panel.png` show the control layout. Amber outlines are generic knob envelopes; teal outlines are button/switch envelopes. Inner outlines are panel openings.
- `generated/panel.dxf` contains millimetre cut geometry including the rounded outside contour. It has no engraving/toolpath compensation.
- `generated/panel_coordinates.csv` lists all coordinates from the front-left corner in the top view, X right and Y toward the rear. DXF uses the corresponding Cartesian Y axis.
- `cad/enclosure.scad` produces a 334 × 157 mm tray and removable panel. Chassis top is 37 mm above the base, with the main knob envelope reaching 57 mm. `part="assembly"` is an exploded inspection view; `part="tray"` and `part="panel"` export the separate solids. The envelope follows the [Pioneer brochure](https://images.myfrenex.com/dataweb/N579N/Allegati/TECH/PEE_RMX1000_8PP_LR.pdf); individual control positions are a project layout, not measurements of an original faceplate.

```sh
python3 tools/generate_hardware.py --preview
python3 tools/generate_hardware.py --check
openscad -D 'part="panel"' -o hardware/generated/panel.stl hardware/cad/enclosure.scad
openscad -D 'part="tray"' -o hardware/generated/tray.stl hardware/cad/enclosure.scad
```

The generator checks faceplate clearances, screw-boss keepouts, unique channels, GPIO conflicts, and SDMMC reservations. The PNG was visually inspected. OpenSCAD is not installed in the development environment. An official universal snapshot download was blocked by Chrome as unverified; the block was not overridden. Solid rendering/export therefore remains unverified. Before cutting a panel, select and measure the actual pots, caps, switches, display, jacks and spring lever, add their mounting and anti-rotation holes, add PCB mounts, and run a full underside interference check. The screw pilots are for a prototype and need insert-specific dimensions for a production enclosure.

## Compute and memory

Use the **64 MB external SDRAM / 65 MB total RAM** Seed variant. The 1 MB variant cannot hold this engine. The [manufacturer's memory guide](https://daisy.audio/pages/memory-what-is-the-difference) distinguishes these variants. The [Seed datasheet](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/Daisy_Seed_datasheet.pdf) specifies the Cortex-M7 platform, board footprint, codec, GPIO and level limits.

The adapter fixes processing at stereo 48 kHz with 64-frame blocks (1.33 ms per block, excluding converter delay). All engine/sample vectors use PMR memory and a coalescing 60 MiB SDRAM arena, installed only after SDRAM initialization. Failure is explicit; large buffers never silently fall back to internal RAM. `rmx_memory_budget` actually prepares the engine, synthesizes the factory banks, replaces them with 64 seconds of stereo sample storage, processes audio, frees everything and checks heap coalescing. The shared sample model carries slot-1 loop/BPM metadata and a 16-second per-bank validator. The boot-time SD loader now installs validated banks before audio starts. The allocation check runs four active sampler loops alongside FX and live roll. Run it for current measured byte counts. This establishes memory capacity on the host, not Cortex-M7 timing or cache/DMA behavior.

## Digital carrier wiring

All external digital and control signals are **3.3 V**. `generated/BoardConfig.h` is generated from the manifest and used by the firmware. D numbers below are Seed GPIO indices, not physical header pin numbers.

| Function | Seed GPIO | Connection |
| --- | --- | --- |
| Button load / clock / data | D0 / D7 / D8 | Four daisy-chained 74HC165, active-low inputs with 10k pull-ups. Tie clock-inhibit low. |
| LED data / clock / latch / OE | D9 / D10 / D13 / D14 | Twelve 74HC595. OE has 47k pull-up to keep outputs dark through reset. Tie SRCLR high. |
| Touch I²C SCL / SDA | D11 / D12 | MPR121 at 0x5A, 4.7k pull-ups to 3.3 V, eight electrodes under a plastic lens. No metal over the sensing area. |
| Analog mux outputs A / B | D15 / D16 | Two 74HC4051 common outputs, 8 scanned inputs each. VEE=GND, INH=GND. |
| Mux S0 / S1 / S2 | D25 / D26 / D27 | Shared address lines, both muxes configured for eight channels in libDaisy. |
| Watchdog heartbeat | D28 | TPS3431 WDI; heartbeat advances only when audio callbacks advance. |
| DSP ready | D17 | 47k pull-down; asserted only after successful audio callbacks, withdrawn on a stalled audio stream. |
| microSD reserved | D1–D6 | Native SDMMC pins. Do not attach the mux or LED chain to these pins. |

74HC165 bit 0 is the first bit read, QH of the register nearest the MCU. For that package, wire input H to bit 0, G to bit 1, through A to bit 7. QH of the next package connects to SER of the previous one. Manifest button channels 0–28 follow the `Button` enum; bit 29 selects Back Spin, bit 30 selects Vinyl Brake, neither selects Echo. Bit 31 selects User. All pressed/selected states pull low. The switches are debounced for five consecutive 1 kHz scans. Bank+pad selects a bank; repeating that chord returns to the internal drum. Overdub+pad deletes a lane. Hold+pad selects silently with Overdub off or mutes the lane with it on, without toggling Hold. Exact bank availability/LED/chord behavior remains subject to reference-unit checks.

74HC595 nearest the MCU drives bits 0–7 on QA–QH; serial QH' goes to SER of the next package. All segments have their own current-limiting resistor. Bits 0/1 are Quantize/Auto, 5/6 source, 7–10 isolator modes, 12 Roll, 17/18 Overdub/Hold, 19–28 Scene selection, 29–32 bank, 33–43 input meter, 44–54 output meter, 55–78 three seven-segment digits (a..g, decimal point unused). Other outputs are reserved; pad activity and touch-strip feedback are not yet driven.

Analog channels 0–10 are listed in `adcParameters`: ten knobs and the release lever. Each pot runs between 3.3 V and ground, with a protected/filtered wiper. A 1 kΩ/10 nF wiper network is a starting point; measure settling and crosstalk before freezing ADC timing. Center-detent controls have a small software dead zone. Calibrated per-control endpoints are still required.

## Audio, power and bypass carrier

The digital development firmware is useful with the module's bench-level audio connections. The final line-level carrier still requires an electrical schematic and PCB. Do not treat the module's codec pins as a completed DJ mixer interface. Rev7 input/output levels and impedance differ from some older Seed references; use the actual [current datasheet](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/Daisy_Seed_datasheet.pdf), not an assumed codec revision.

Target the original's master/send-return gain ranges, 20 dB headroom and noise/distortion specifications. Provide selectable input attenuation, output recovery gain, input impedance/protection, AC coupling/bias where required, RF filtering and a calibrated unity setting. Input/output gains must be designed together: software `WetOnly` is parallel wet extraction, not the original rear-panel analog gain switch. A candidate +4 dBu nominal / +24 dBu maximum input is 1.228 / 12.283 Vrms; 3.6 Vpp codec input corresponds to about 1.273 Vrms, so roughly 0.104 attenuation would be required at the maximum level. This calculation is a design constraint, not a verified circuit. The Seed's 1 Vrms full-scale output would then need matching external gain/headroom. Choose the analog rails, op-amps and resistor networks with those constraints before laying out the board.

Use two non-latching DPDT signal relays (one per channel). NC connects input directly to output; NO selects processed output. In a balanced design both signal legs must switch. `RELAY_ENABLE = DSP_READY AND WATCHDOG_OK AND POWER_GOOD AND NOT MANUAL_BYPASS`. No direct coil load on a GPIO: use a rated driver and flyback suppression. Pull DSP_READY down. The watchdog alone is insufficient at boot because its timeout may not have elapsed. Use the [TPS3431 datasheet](https://www.ti.com/lit/ds/symlink/tps3431.pdf) to set and verify a nominal 50 ms timeout, including tolerance. Add analog output mute/settling control to avoid relay pops. Power-loss, crash and boot behavior must be measured before live use.

The rear CAD DC hole and BOM are placeholders for a regulated 5 V bench supply path. Final protection, supply isolation, analog rails, return-current paths, relay inrush, EMC and thermal tests remain design work. No PCB/Gerber release exists yet.

## Firmware build and acceptance

`firmware/daisy/main.cpp` connects the shared engine, SDRAM allocator, analog mux scan, button chains, touch sensor, basic LED display and hardware watchdog signals. ADC/touch/LED transactions run in the foreground; the audio callback does only DSP and advances a heartbeat counter. Touch failure releases its gesture.

```sh
make -C /path/to/libDaisy
make -C firmware/daisy LIBDAISY_DIR=/absolute/path/to/libDaisy
```

The verified configuration uses Arm GNU 14.3.Rel1 (C++20), libDaisy 8.1.0 with unshifted I²C register addresses, and `BOOT_QSPI` at 0x90040000; it requires a compatible Daisy bootloader. The firmware has now cross-compiled and linked with Arm GNU 14.3.Rel1 and libDaisy 8.1.0 (`9498417add4a4c76bc10737d5e9f43750a4da639`), including its exact Arm/ST submodule revisions. These dependencies live in `.tools`, with pins/checksums in `firmware/daisy/dependencies.lock.json`; no global compiler installation was made. The compiler package matches Arm's published SHA-256. The actual ELF, map and current source hashes pass `tools/check_firmware.py`. This is a cross-build claim only: the image has not been flashed or run on a board. USB MIDI, SD effect presets/RSD interoperability, nonvolatile calibration, touch baseline tuning, complete lighting, and embedded watchdog fault-injection tests remain outstanding.

First bring-up: check rails and relay NC continuity; verify all 32 switch inputs and 11 analog channels; verify touch-release on I²C disconnect; scope callback timing and maximum interrupt latency with all FX/sample lanes active; record a physical round trip; stop the audio ISR and main loop separately and verify dry bypass; then test power loss and a two-hour control/audio soak. Match sound against a physical reference only after the electrical route is stable.


## Reproduce and inspect the firmware build

`tools/setup_firmware.py` accepts pinned source archives downloaded with a browser (`.tar` after Safari decompression is supported) or downloads them with `--download` when shell networking is available. It verifies the decompressed tar hashes before extraction. Compiler package extraction unpacks the verified payload locally and does not run installer scripts.

```sh
python3 tools/setup_firmware.py --archives /path/to/downloads --compiler-package /path/to/arm-gnu-toolchain-14.3.rel1-darwin-arm64-arm-none-eabi.pkg
make -C .tools/libDaisy-8.1.0 GCC_PATH="$PWD/.tools/arm-gnu-14.3/Payload/bin" -j4
make -C firmware/daisy clean
make -C firmware/daisy -j4
python3 tools/check_firmware.py
python3 tools/check_firmware.py --check
```

An existing compiler can be supplied as `--gcc-bin /path/to/bin`. The SDK setup prints the correct build command and writes a local `.tools/firmware-env.mk`. `.tools` and firmware build outputs are ignored. Download URLs and archive roots are in the lock file.

The current [build record](../firmware/daisy/build-record.json) proves a 32-bit ARM hard-float image, QSPI boot-vector placement and the 60 MiB external audio arena. The linked image before SD support used 160,324 QSPI bytes, 40,424 AXI SRAM bytes and 16,704 DMA-region bytes. The build record contains the current values after SD/FatFS integration. The current engine and bank objects occupy 25,856 and 800 bytes on this ARM ABI, including the separate internal-source descriptors and captured event identity. The 128 KiB DTCM stack high-water mark is unmeasured. The record includes SDK-source/library and project-source/artifact hashes so `--check` rejects a stale result.

The upstream startup FP-register diagnostic, unused nosys syscall stubs and an RWX ELF segment warning remain recorded rather than suppressed. No POSIX/newlib console or filesystem syscall functionality is claimed; SD access uses FatFS directly, and audio and sample buffers still use the bounded arena. Physical boot/relay behavior, cache/DMA behavior, stack usage and worst-case callback timing require board bring-up.


## SD sample preparation and boot loading

The firmware reads a project sample layout from a FAT-formatted card at boot, before starting audio. It supports 48 kHz mono/stereo signed PCM WAVs at 16 or 24 bits, with at most 16 seconds across each bank's four slots. Loop/BPM metadata follows the slot-1-only rule and 70–200 BPM range. This is a project layout, separate from Pioneer RSD/SD data; native RSD import and effect-preset loading remain unfinished.

Prepare a new folder from a saved desktop preset:

```sh
./build/rmx_card_export Performance.rmx /path/to/new-card-folder
```

Copy that folder's `RMX` subfolder to the card root. Export requires an unused destination and commits the folder only after conversion succeeds. It writes stereo PCM24 and preserves sample loop/BPM metadata. Source files must already be 48 kHz and within PCM peak range; the tool rejects unsupported rates/overrange peaks instead of silently changing them. General desktop sample imports remain wider. The export contains sample banks, not Scene/Isolate/Release settings or MIDI mappings.

The folder contains `SAMPLES.TXT` and files named `B1S1.WAV` through `B4S4.WAV`. Manifest slots are numbered 0–15 and banks 0–3:

```text
RMX_SAMPLES 1
bank 0
slot 0 1 128.250000
slot 1 0 120.000000
```

A slot row requests its bank implicitly; `bank 0` can also request an entirely empty bank. Each requested bank replaces all four slots; omitted slots become silent. Unrequested banks stay unchanged. A format, read, close, capacity or allocation failure leaves the failing bank's four old slots intact while other valid banks may install. A malformed manifest installs nothing. Card absence or a missing manifest retains the synthesized defaults.

`CardStorage` keeps its FatFS/file objects and a 32-byte-aligned read buffer in AXI SRAM. DMA never targets decoder stack buffers or sample SDRAM directly. Reads realign partial file positions before allowing full-sector transfers. The actual linker check verifies that the card object is aligned and lies inside AXI SRAM; libDaisy performs cache maintenance. The card is unmounted before audio begins, and no card access occurs in the callback. A card error blinks the onboard LED; `cardState` and `card.report` retain detailed bring-up status.

Host fixtures verify PCM/channel conversion, fragmented reads, odd RIFF chunks, data-before-format ordering, truncation/unsupported formats, bank overflow, missing files, read/close failure rollback, allocator mismatch, SDRAM exhaustion and exporter-to-firmware-decoder roundtrips. Replacing all 64 seconds of banks while retaining internal drums peaks at 58,040,496 bytes inside the 62,914,536-byte usable host arena; active playback still makes no arena allocations. These tests and a successful cross-build do not prove SDMMC wiring, card compatibility, cache behavior, power-loss handling or real-board boot timing. Those checks remain required.

Firmware boots with four synthesized internal drums and empty SD sample banks. Loading or clearing an SD bank preserves the internal drums. Bank indicators are dark in internal mode. Selecting an empty or unavailable bank currently selects silence; matching the original availability/blink feedback remains unfinished. With internal drums retained, the host full-card replacement peak is 58,040,496 bytes inside the 62,914,536-byte usable arena. The latest linked image uses 194,100 QSPI bytes, 49,752 AXI SRAM bytes and 18,204 DMA-region bytes; these sizes do not establish target runtime performance.


The eight touch positions use the same User beat assignments as the desktop engine, including triplets. The live-input buffer now holds twelve seconds, so eight beats at 40 BPM is not clipped. Default retains the previous project beat layout. Firmware still lacks the effect-preset transfer/loading path needed to install custom User assignments without changing code; desktop settings and the shared API already expose them. Matching held-capture division/pitch changes and Slip/Divide modes remains outstanding.

C++ compiler flags must retain recursive Make expansion: the dependency filename contains the per-object automatic target variable. The former eager assignment discarded it and could leave incompatible engine/adapter objects after a header edit. The current Makefile emits `.d` files for all C++ units; `check_firmware.py` requires them and checks dependency/object/link freshness plus content hashes before writing or checking a record. `tests/firmware_build_tests.py` exercises rejection of stale headers/makefiles, unlinked objects, missing/empty dependency files, wrong targets and content changes with restored timestamps. The Make dry-run check confirmed parameter-header changes rebuild the adapter and engine. This is build validation, not target execution.
