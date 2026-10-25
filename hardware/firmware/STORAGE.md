# F05 boot storage

The standalone runtime now reads an optional FAT-formatted SD card at cold boot. Storage work finishes before audio callbacks, heartbeat, converter activation or relay permission begin. It uses the pinned libDaisy FatFs adapter directly; there is no POSIX filesystem access. Files are opened read-only, closed and unmounted before audio starts. This has host and ARM build evidence, not physical SD-card or complete-unit qualification.

## Card layout

Use a directory named `RMX` at the card root. All files are optional:

| Path | Purpose |
| --- | --- |
| `RMX/BOOT.TXT` | Boot preset, header `RMX_BOOT 1` |
| `RMX/USER.TXT` | User settings, header `RMX_USER 1` |
| `RMX/B1S1.WAV` through `RMX/B4S4.WAV` | Four banks of four replacement samples |

Missing sample files preserve their factory slot. Bad files preserve that slot too, and the debugger-visible `cardReport` records the error. Each asset commits only after decoding **and closing** succeeds. A valid boot preset, valid user file and valid samples load independently. A malformed profile never applies a partial parameter set. Boot attempts reset persistent values to defaults before loading, so a missing or rejected profile does not reuse old profile values.

WAV support is mono/stereo little-endian PCM16/24/32 or IEEE float32 at 8–96kHz. Samples must contain 2–96000 decoded frames and last at most 2 seconds. Float input must be finite and within [-1,1]. RF64, compressed/extended WAV, duplicate format/data chunks, invalid block alignment, truncated chunks and RIFF size mismatches are rejected. Chunks can appear in either order and odd chunk sizes include the RIFF pad byte. There are at most 64 scanned chunks and 1 MiB per encoded WAV. The decoded bank cap is 12,288,000 bytes; one staged candidate is at most 768,000 bytes. This remains within the existing 48 MiB arena reservation, but actual timing and card behavior need bench confirmation. Before reserving a candidate, the cold-boot adapter checks a contiguous free block in the actual audio arena. All candidates reserve at least 4096 bytes so they use that arena instead of the small-allocation heap. No audio/other arena allocation interleaves the check and reserve; fragmentation or insufficient space returns a memory error and retains the factory slot. This preflight relies on the pinned toolchain’s empty-vector reserve allocating the requested capacity, and is not a general concurrent-allocation guarantee.

## Profiles

Profiles use one `param <id> <decimal value>` line per value. Blank lines, CRLF and full-line `#` comments are accepted. Duplicate/unknown parameters, unknown lines, nonfinite/out-of-range values and nonintegral discrete values reject the whole profile. A profile is at most 4096 bytes with 127 characters per line. These are project boot formats, not a claim of Pioneer RSD or complete desktop preset compatibility.

Example `BOOT.TXT`:

```text
RMX_BOOT 1
param tempo 128
param quantize 1
param scene_type 1
param bank 0
```

Example `USER.TXT`:

```text
RMX_USER 1
param low_crossover 250
param high_crossover 4000
param feedback 0.65
param reverb_decay 0.72
param noise_color 0.5
param swing 0
```

The User file permits exactly those six advanced settings. The existing physical Default/User selector determines whether the DSP uses them. The boot preset permits known runtime parameters except bypass, wet-only routing, scene engagement, release lever/type, hold, overdub and the physical Default/User selector. Physical knob readings and the release selector remain authoritative during initialization. Card data cannot restore a held lever, engage an effect or grant relay permission. Calibration remains in the two existing QSPI sectors at `0x007f0000` and `0x007f1000`; the SD loader never writes them.

## DMA, timing and evidence

The BOOT_SRAM linker's ordinary `.bss` is DTCM. The dedicated `.sdmmc_bss` allocation instead places the FatFs filesystem/file sector windows and 4096-byte bounce buffer in 32-byte-aligned AXI SRAM. `StorageMemory.ld` checks the region, and the verifier checks actual ELF symbol addresses and sections for both profiles. The storage allocation is explicitly initialized after `hw.Init`; audio DMA reserves remain separate. The SDK cleans enclosing cache lines before DMA and invalidates them after completion. Any FatFs metadata sharing those lines is unchanged during the synchronous transfer; the complete allocation and a trailing guard isolate unrelated data. Physical DMA/cache behavior still requires measurement.

An 8-second budget is checked between filesystem operations and before installing an asset. It is **not a hard 8-second deadline**: an in-flight SDK call may exceed it, and the pinned SD driver has 30-second polling limits. Once the operation returns, an expired budget prevents committing that asset or opening later assets. Processing remains disarmed throughout. No runtime card reload or write path is present.

Reproduce from the repository root:

```sh
python3 -m hardware.firmware.verify_storage --toolchain /path/to/arm-toolchain/bin
```

This builds all 27 standalone host CTest groups and both ARM profiles in separate storage build directories. Source hashes, original SDK hashes, actual sections/SD buffer addresses, test XML and logs are recorded under `hardware/validation/standalone-storage/`. Existing historical firmware and PCB records remain untouched.

The implementation follows the pinned SDK's [FatFS interface](https://github.com/electro-smith/libDaisy/blob/f715e4875b2d28445d0c11a0a17f064a248f69d0/src/sys/fatfs.h) and [SD disk driver](https://github.com/electro-smith/libDaisy/blob/f715e4875b2d28445d0c11a0a17f064a248f69d0/src/util/sd_diskio.c), [FatFs read semantics](https://elm-chan.org/fsw/ff/doc/read.html) and [RIFF chunk layout](https://learn.microsoft.com/en-us/windows/win32/xaudio2/resource-interchange-file-format--riff-).

Remaining physical work includes the J12 socket/detect assembly, 3.3 V current/inrush and supply margins, pull-ups and signal integrity, DMA/cache validation, malformed/removable-card testing, boot-time measurement and powered audio/relay qualification. Do not infer an electrically complete or build-ready device from successful loading tests.
