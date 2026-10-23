# RMX hardware prototypes

**Active budget variant:** [B1 5V design](budget/README.md), with a routed carrier PCB, source-hashed native checks, split-panel fit meshes and an explicitly provisional cost ledger. The A0.2 design below remains a separate higher-headroom variant; its BOM is not the budget shopping list.

## A0.2 reference design

This is the physical implementation path toward the full clone. It is a development design, not a fabrication release or an assertion of measured RMX sound. Deliverables include the common control/pin manifest, generated panel DXF/SVG, editable OpenSCAD enclosure, Daisy firmware adapter, and the [A0.2 carrier circuit set](electrical/carrier.md): eight new pin-connected KiCad/SVG/JSON sheets alongside the bypass permission sheet, with consolidated BOM and connection tables. The integrated KiCad 10 project passes native ERC and physical-component/netlist checks; see the source-hashed [record](electrical/native-check.json). Electrical drafts are ahead of the A0 rear-panel CAD; component/footprint completion, PCB layout, physical fit and commissioning remain open.

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

The generator checks faceplate clearances, screw-boss keepouts, unique channels, GPIO conflicts, and SDMMC reservations. The PNG was visually inspected. An earlier official universal snapshot download was blocked by Chrome as unverified; the block was not overridden. A separate pre-existing OpenSCAD bundle has since been located, but has not been used to validate these solids. Solid rendering/export remains unverified. Before cutting a panel, select and measure the actual pots, caps, switches, display, jacks and spring lever, add their mounting and anti-rotation holes, add PCB mounts, and run a full underside interference check. The screw pilots are for a prototype and need insert-specific dimensions for a production enclosure.

## Compute and memory

Use the **64 MB external SDRAM / 65 MB total RAM** Seed variant. The 1 MB variant cannot hold this engine. The [manufacturer's memory guide](https://daisy.audio/pages/memory-what-is-the-difference) distinguishes these variants. The [Seed datasheet](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/Daisy_Seed_datasheet.pdf) specifies the Cortex-M7 platform, board footprint, codec, GPIO and level limits.

Component selection should favor New Zealand suppliers. The [NZ sourcing record](sourcing-nz.md) identifies a local Seed listing, currently pre-order/out of stock, and separates local suppliers from overseas warehouse stock. Availability remains a procurement requirement; this is not a ready-to-order full hardware kit.

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
| Watchdog heartbeat | D28 | TPS3435AFACADDFRQ1 WDI and both U24 clocks; heartbeat advances only when audio callbacks advance. |
| DSP ready | D17 | 47k pull-down; asserted only after successful audio callbacks, withdrawn on a stalled audio stream. |
| microSD reserved | D1–D6 | Native SDMMC pins. Do not attach the mux or LED chain to these pins. |

74HC165 bit 0 is the first bit read, QH of the register nearest the MCU. For that package, wire input H to bit 0, G to bit 1, through A to bit 7. QH of the next package connects to SER of the previous one. Manifest button channels 0–28 follow the `Button` enum; bit 29 selects Back Spin, bit 30 selects Vinyl Brake, neither selects Echo. Bit 31 selects User. All pressed/selected states pull low. The switches are debounced for five consecutive 1 kHz scans. Bank+pad selects a bank; repeating that chord returns to the internal drum. Overdub+pad deletes a lane. Hold+pad selects silently with Overdub off or mutes the lane with it on, without toggling Hold. Exact bank availability/LED/chord behavior remains subject to reference-unit checks.

74HC595 nearest the MCU drives bits 0–7 on QA–QH; serial QH' goes to SER of the next package. All segments have their own current-limiting resistor. Bits 0/1 are Quantize/Auto, 5/6 source, 7–10 isolator modes, 12 Roll, 17/18 Overdub/Hold, 19–28 Scene selection, 29–32 bank, 33–43 input meter, 44–54 output meter, 55–78 three seven-segment digits (a..g, decimal point unused). Other outputs are reserved; pad activity and touch-strip feedback are not yet driven.

Analog channels 0–10 are listed in `adcParameters`: ten knobs and the release lever. Each pot runs between 3.3 V and ground, with a protected/filtered wiper. A 1 kΩ/10 nF wiper network is a starting point; measure settling and crosstalk before freezing ADC timing. Center-detent controls have a small software dead zone. Calibrated per-control endpoints are still required.

## Audio, power and bypass carrier

The digital development firmware is useful with the module's bench-level audio connections. The [A0.2 line-level, power and relay circuits](electrical/carrier.md) are now drawn as electrical drafts; they still require part/footprint completion, native review, protection work and a PCB. Do not treat the module's codec pins or the new draft as a completed DJ mixer interface. Rev7 input/output levels and impedance differ from some older Seed references; use the actual [current datasheet](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/Daisy_Seed_datasheet.pdf), not an assumed codec revision.

Target the original's master/send-return gain ranges, 20 dB headroom and noise/distortion specifications. Provide selectable input attenuation, output recovery gain, input impedance/protection, AC coupling/bias where required, RF filtering and a calibrated unity setting. Input/output gains must be designed together: software `WetOnly` is parallel wet extraction, not the original rear-panel analog gain switch. A candidate +4 dBu nominal / +24 dBu maximum input is 1.228 / 12.283 Vrms; 3.6 Vpp codec input corresponds to about 1.273 Vrms, so roughly 0.104 attenuation would be required at the maximum level. This calculation is a design constraint, not a verified circuit. The Seed's 1 Vrms full-scale output would then need matching external gain/headroom. Choose the analog rails, op-amps and resistor networks with those constraints before laying out the board.

The A0.2 relay sheet selects three standard G5V-2 DC5 relays: two output selectors with dry on NC, plus a stereo line-input mute. DMN3023L coil drivers, local supervisor clamps, 5 V HCT Schmitt buffers, TVS suppression and delayed reconnect are drawn. The line interface is unbalanced RCA/TS; it bonds the spare switched conductors to ground. Permission requires DSP_READY, watchdog health, analog rail/reference health, digital supply health and manual bypass released. Connectivity and static budgets are host-tested; switching, startup, temperature and click behavior remain unverified.

The earlier nominal 50 ms TPS3431 recommendation was incorrect: its adjustable equation has a 55 ms offset. The draft now uses [TPS3435AFACADDFRQ1](https://www.ti.com/lit/gpn/tps3435-q1), with a 10.1nF CWD network for **49.995 ms nominal** and a separate 10nF CRST network for a nominal 49.5 ms fault pulse. Adjustable timing has ±20% device tolerance; combined with initial 1% capacitors the watchdog interval is 39.596–60.594 ms, before capacitor temperature effects, parasitics and relay/driver delay. Define and verify maximum complete fault-to-dry latency separately; this is not a 50 ms maximum response claim.

The selected watchdog's WDO is an active-low open-drain **pulse**, followed by a startup frame that exits on a valid falling WDI edge. A direct AND gate or single rising-edge permission stage is insufficient. The [draft permission circuit](electrical/README.md) asynchronously clears both stages of a 74LVC74APW on any health fault and requires two fresh rising heartbeat edges, with an intervening falling edge that starts watchdog monitoring, before reconnecting. Its emitted CAD connectivity and ideal digital/frame scenarios are host-tested, and it passes native ERC as part of the integrated carrier project. Reset/clock/hold margins and physical behavior remain unverified. Add analog output mute/settling control to avoid relay pops. Measure total fault-to-dry latency, power-loss, crash and boot behavior before live use.

The old rear CAD DC hole is a placeholder. The A0.2 draft uses regulated external 12 V DC, a 5 V buck and isolated 24 V modules post-regulated to approximately ±20 V. Its power/audio topology and remaining surge/protection/current-budget issues are documented in the carrier design. Update the panel for RCA, TS, mode, power and actual connector dimensions before fabrication. No PCB/Gerber release exists yet.

## Firmware build and acceptance

`firmware/daisy/main.cpp` connects the shared engine, SDRAM allocator, analog mux scan, button chains, touch sensor, basic LED display and hardware watchdog signals. ADC/touch/LED transactions run in the foreground; the audio callback does only DSP and advances a heartbeat counter. Touch failure releases its gesture.

```sh
make -C /path/to/libDaisy
make -C firmware/daisy LIBDAISY_DIR=/absolute/path/to/libDaisy
```

The verified configuration uses Arm GNU 14.3.Rel1 (C++20), libDaisy 8.1.0 with unshifted I²C register addresses, and `BOOT_QSPI` at 0x90040000; it requires a compatible Daisy bootloader. The firmware has now cross-compiled and linked with Arm GNU 14.3.Rel1 and libDaisy 8.1.0 (`9498417add4a4c76bc10737d5e9f43750a4da639`), including its exact Arm/ST submodule revisions. These dependencies live in `.tools`, with pins/checksums in `firmware/daisy/dependencies.lock.json`; no global compiler installation was made. The compiler package matches Arm's published SHA-256. The actual ELF, map and current source hashes pass `tools/check_firmware.py`. This is a cross-build claim only: the image has not been flashed or run on a board. USB MIDI, original SD/RSD interoperability, nonvolatile User storage/calibration, touch baseline tuning, complete lighting, and embedded watchdog fault-injection tests remain outstanding.

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

The current [build record](../firmware/daisy/build-record.json) proves a 32-bit ARM hard-float image, QSPI boot-vector placement and the 60 MiB external audio arena. The linked image before SD support used 160,324 QSPI bytes, 40,424 AXI SRAM bytes and 16,704 DMA-region bytes. The build record contains the current values after SD/FatFS integration. The current engine and bank objects occupy 23,744 and 800 bytes on this ARM ABI, including the separate internal-source descriptors, captured event identity and current tempo tracker. The 128 KiB DTCM stack high-water mark is unmeasured. The record includes SDK-source/library and project-source/artifact hashes so `--check` rejects a stale result.

The upstream startup FP-register diagnostic, unused nosys syscall stubs and an RWX ELF segment warning remain recorded rather than suppressed. No POSIX/newlib console or filesystem syscall functionality is claimed; SD access uses FatFS directly, and audio and sample buffers still use the bounded arena. Physical boot/relay behavior, cache/DMA behavior, stack usage and worst-case callback timing require board bring-up.


## SD sample preparation and boot loading

The firmware reads a project sample layout and User profile from a FAT-formatted card at boot, before starting audio. It supports 48 kHz mono/stereo signed PCM WAVs at 16 or 24 bits, with at most 16 seconds across each bank's four slots. Loop/BPM metadata follows the slot-1-only rule and 70–200 BPM range. This is a project layout, separate from Pioneer RSD/SD data; original import/export compatibility remains unfinished.

Prepare a new folder from a saved desktop preset:

```sh
./build/rmx_card_export Performance.rmx /path/to/new-card-folder
```

Copy that folder's `RMX` subfolder to the card root. Export requires an unused destination and commits the folder only after conversion succeeds. It writes stereo PCM24, sample loop/BPM metadata and the preset's stored User settings, even when Default was selected when saving. Source files must already be 48 kHz and within PCM peak range; the tool rejects unsupported rates/overrange peaks instead of silently changing them. General desktop sample imports remain wider. Performance controls, MIDI mappings and physical switch positions are excluded from the User profile.

Use `--settings-only` to export User settings without reading audio files, or `--samples-only` to export sample banks without a User profile. For a partial export, copy its files into the card's existing `RMX` directory. A settings-only card can contain just `RMX/USER.TXT`; samples and settings load independently.

```sh
./build/rmx_card_export Performance.rmx /path/to/new-settings-folder --settings-only
```

`USER.TXT` starts with `RMX_USER 1`, followed by stable-ID rows such as `param x_pad_beat_1 7`. It carries only implemented advanced User settings. The streaming parser is bounded to 16 KiB and 128-byte lines, allocates no memory, and preserves current User values if validation, reading or file close fails. Unknown/duplicate IDs, non-User fields, nonfinite/out-of-range values and fractional discrete choices are rejected. Omitted User fields use defaults. Install a valid profile from a matching software/firmware schema; the physical Default/User switch selects its use without altering the stored values. The card profile does not restore an engaged release lever, start recording, select a sample bank or move physical controls. USB synchronization, live insertion/loading and internal nonvolatile User storage remain unfinished.

The folder contains `SAMPLES.TXT` and files named `B1S1.WAV` through `B4S4.WAV`. Manifest slots are numbered 0–15 and banks 0–3:

```text
RMX_SAMPLES 1
bank 0
slot 0 1 128.250000
slot 1 0 120.000000
```

A slot row requests its bank implicitly; `bank 0` can also request an entirely empty bank. Each requested bank replaces all four slots; omitted slots become silent. Unrequested banks stay unchanged. A format, read, close, capacity or allocation failure leaves the failing bank's four old slots intact while other valid banks may install. A malformed sample manifest installs no sample banks, but an independent valid User profile can still load. Card absence or a missing sample manifest leaves internal drums and the current bank assets unchanged.

`CardStorage` keeps its FatFS/file objects and a 32-byte-aligned read buffer in AXI SRAM. DMA never targets decoder stack buffers or sample SDRAM directly. Reads realign partial file positions before allowing full-sector transfers. The actual linker check verifies that the card object is aligned and lies inside AXI SRAM; libDaisy performs cache maintenance. The card is unmounted before audio begins, and no card access occurs in the callback. A card error blinks the onboard LED; `cardState`, `card.report` and `card.settingsError` retain detailed bring-up status. Rejection of one data type does not prevent the other loading.

Host fixtures verify PCM/channel conversion, fragmented reads, odd RIFF chunks, data-before-format ordering, truncation/unsupported formats, bank overflow, missing files, read/close failure rollback, allocator mismatch, SDRAM exhaustion and exporter-to-firmware-decoder roundtrips. Replacing all 64 seconds of banks while retaining internal drums peaks at 58,040,496 bytes inside the 62,914,536-byte usable host arena; active playback still makes no arena allocations. These tests and a successful cross-build do not prove SDMMC wiring, card compatibility, cache behavior, power-loss handling or real-board boot timing. Those checks remain required.

Firmware boots with four synthesized internal drums and empty SD sample banks. Loading or clearing an SD bank preserves the internal drums. Bank indicators are dark in internal mode. Selecting an empty or unavailable bank currently selects silence; matching the original availability/blink feedback remains unfinished. With internal drums retained, the host full-card replacement peak is 58,040,496 bytes inside the 62,914,536-byte usable arena. The latest linked image uses 205,704 QSPI bytes, 47,640 AXI SRAM bytes and 18,204 DMA-region bytes; these sizes do not establish target runtime performance.


The eight touch positions use the same User beat assignments as the desktop engine, including triplets. The live-input buffer holds twelve seconds, so eight beats at 40 BPM is not clipped. Default retains the previous project beat layout; custom assignments now load through `USER.TXT` at boot. Matching held-capture division/pitch changes and Slip/Divide modes remains outstanding.

C++ compiler flags must retain recursive Make expansion: the dependency filename contains the per-object automatic target variable. The former eager assignment discarded it and could leave incompatible engine/adapter objects after a header edit. The current Makefile emits `.d` files for all C++ units; `check_firmware.py` requires them and checks dependency/object/link freshness plus content hashes before writing or checking a record. `tests/firmware_build_tests.py` exercises rejection of stale headers/makefiles, unlinked objects, missing/empty dependency files, wrong targets and content changes with restored timestamps. The Make dry-run check confirmed parameter-header changes rebuild the adapter and engine. This is build validation, not target execution.
