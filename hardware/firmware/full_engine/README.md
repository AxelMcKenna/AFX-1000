# F06 maintained-engine standalone candidate

This separate candidate builds the maintained DSP sources directly for the standalone Daisy hardware. It replaces the F05 runtime snapshot only when explicitly built here; the F05 firmware, historical B1 adapter and previous review archives remain available. This is a build/host-validation candidate, not a hardware release.

The current engine exposes 152 parameters. Its 122 advanced User settings use the same `CardSettings` reader as the desktop engine, while physical gains, selectors and momentary controls stay under hardware control. The boot loader supports the project boot/User formats and bounded WAV loading described in the [F05 storage notes](../STORAGE.md). Each file remains limited to 96,000 decoded frames and two seconds. It does not implement original RMX RSD files, card writing, live reload or complete desktop/RMX media compatibility.

DSP and sample storage use a 60 MiB bounded PMR arena in SDRAM. Engine, bank and controls are constructed after hardware SDRAM and the arena are initialized. The four factory sounds remain available independently of the 16 user slots. Tests exercise the actual `FixedArena` preflight-to-PMR decode transaction, fragmentation/coalescing, allocation failure after a successful probe, and rejection of incompatible candidate allocators. Optional loading returns `Error::Memory` and preserves the old sample. The host memory test also checks zero audio-callback allocation; this is not a measurement of real MCU timing or SDRAM/cache behavior.

The original 278,916-byte interpolation table made the maintained engine overflow the 480 KiB SRAM boot image. `generate_kernels.py` stores 177,540 bytes using exact mirror/XOR differences. At boot, `KernelTransport.cpp` restores all 69,729 float words into a separate 278,916-byte SDRAM region and checks CRC before any audio starts. The compiler independently checks every level's original coefficient CRC. No coefficient is quantized. Invalid or missing initialization keeps sample reads silent. The callback performs no table construction or decoding.

The root `SampleReader.h` has one explicit opt-in, `RMX_EMBEDDED_COMPRESSED_KERNELS`. Without it the existing immutable compile-time table remains in use. Both F06 builds define it. All program instructions remain in SRAM, so calibration writes to QSPI sectors `0x007f0000` and `0x007f1000` do not disable the memory containing executing code. SDMMC buffers retain their separate 32-byte-aligned AXI SRAM section.

The [control recovery policy](CONTROL_RECOVERY.md) validates a complete sensor frame before dispatch, suppresses held inputs across boot/fault recovery, and requests a guaranteed callback Panic independently of queue capacity. Panic deliberately clears the recorded sequence, scene engagement and isolator bands. It is a conservative fault response that requires fresh gestures.

```sh
cmake -S hardware/firmware/full_engine -B build/full-engine-host -DCMAKE_BUILD_TYPE=Release
cmake --build build/full-engine-host --parallel 4
ctest --test-dir build/full-engine-host --output-on-failure
python3 hardware/firmware/full_engine/verify.py \
  --toolchain build-hardware/tools/arm-expanded/Payload/bin \
  --sdk build-hardware/libDaisy
```

`verify.py` checks the pinned SDK checkout, rebuilds its library from clean sources, records the actual compiler version and SDK archive hash, regenerates and compares the exact kernel payload, runs the host suites and makes clean ARM builds for onboard and external converter profiles. It checks the complete range of every allocated executable ELF section for SRAM execution, as well as bounded SDRAM, separated DMA buffers, callback integration and the absence of uncompressed reference kernels. Source and binary hashes are written to `hardware/validation/full-engine/verification.json`. The script never flashes a device.

Physical sensor wiring and ranges, SD power/current/boot behavior, converter/audio operation, callback deadlines, failure injection and the complete power/thermal/mechanical assembly still require actual measurements. Passing these software checks cannot establish that the complete unit works perfectly.
