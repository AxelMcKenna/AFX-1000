# Standalone firmware runtime

This directory preserves the standalone branch's DSP, control interfaces and portable host tests. The incoming runtime differs from the desktop engine on `main`, whose larger parameter set, sample storage, MIDI/Link integration and adapters remain in the root `include/` and `src/` directories. These are separate build targets with separate include paths; changes to one runtime do not qualify the other.

`source.json` records the incoming commit, original paths and hashes of the preserved files. Their contents are unchanged. The CMake files adapt the portable tests to this directory and the firmware headers in `hardware/firmware/`.

From the repository root:

```sh
cmake -S hardware/runtime -B build/standalone-runtime -DCMAKE_BUILD_TYPE=Release
cmake --build build/standalone-runtime --parallel 4
ctest --test-dir build/standalone-runtime --output-on-failure
```

The standalone firmware Makefile selects this runtime explicitly. The earlier B1 adapter in `firmware/daisy/` continues to select the desktop engine. Neither runtime has been qualified on the complete standalone hardware. The [F05 extension](../firmware/STORAGE.md) adds boot-only SD samples/presets/user settings. Added storage files and current test/build evidence are separate from the unmodified incoming source snapshot in `source.json`. Runtime writing/reloading, physical timing, audio and assembly validation remain unfinished.
