# Mac packages

Build a fresh universal Release tree with the pinned local JUCE checkout:

```sh
cmake -S . -B build-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=ON \
  -DRMX_JUCE_PATH=/absolute/path/to/JUCE-8.0.6 \
  '-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64'
cmake --build build-release --parallel 4
ctest --test-dir build-release --output-on-failure
python3 tools/package_macos.py --build-dir build-release --output-dir build/packages-new
```

The destination must not exist. The packager checks every bundle's architecture, signs copies, verifies those signatures and publishes the complete output directory in one rename. Original build products are untouched.

Outputs:

- `RMX-macOS-universal.zip`: native app and notices.
- `RMX-Plugins-universal.zip`: AU/VST3 bundles and dependency license files, when plugins are enabled.
- `RMX-source.zip`: project source with fixed ZIP timestamps, file permissions and SHA-256 manifest.
- `RMX-dependencies.zip`: actual configured JUCE and optional Link source trees, including their notices. This is separate from the project source snapshot.
- `manifest.json`: architectures, signing mode, source hashes, dependency source inventory, build choices and package hashes.
- `SHA256SUMS`: hashes for the archives and manifest.

Verify downloads with `shasum -a 256 -c SHA256SUMS` in the package folder. Source ZIP content is reproducible for identical inputs and executable permissions. Signed binary ZIPs are not claimed to be reproducible byte for byte.

The default ad-hoc signature is for a development preview. It is not Developer ID signing or notarization. Pass `--sign-identity 'Developer ID Application: ...'` to use your signing identity; notarization is still a separate Apple operation. No credentials are stored by the script.

## Native panel artwork

Current native/plugin builds use `assets/panel.png`, generated from project drawing code rather than a hardware photograph. Control positions stay shared with the hit areas. Regenerate it on a Mac:

```sh
cmake --build build-release --target rmx_panel_art
./build-release/rmx_panel_art assets/panel.png
```

Use a fresh build tree when replacing an old app bundle so obsolete resources are not carried into packaging.

## Dependency and source licensing

See [the dependency notices](../THIRD_PARTY_NOTICES.md). A project license has not yet been selected. That decision remains with the owner. JUCE-based builds use JUCE's AGPLv3 or commercial license route; optional Link and embedded SDK components retain their own terms. Packaging source and notices is evidence of the shipped inputs, not a declaration that every license obligation or distribution requirement has been satisfied.

## Runtime acceptance

Build/signature checks do not establish DAW compatibility, FLX cue routing, physical round-trip latency or live-set reliability. Use [the reference and runtime workflow](reference-validation.md) to collect host, controller, reference-unit and hardware evidence. Offline soak reports must state simulated audio duration separately from wall-clock runtime.

## Plugin runtime smoke host

With a plugin build configured:

```sh
cmake --build build-release --target RMXPluginProbe --parallel 4
./build-release/RMXPluginProbe_artefacts/Release/RMXPluginProbe \
  "$PWD/build-release/RMXPlugin_artefacts/Release/VST3/RMX.vst3" \
  > build-release/vst3-runtime.json
```

The host loads the explicit bundle, without an editor or audio device, and checks neutral stereo, parameter endpoints, Scene/Isolate modes, state recall, MIDI pads and supported rate/block/transport combinations. A watchdog bounds hangs. A plugin crash can still terminate the process. This is smoke-host evidence, not DAW certification or validation of UI timers, dialogs and user sample recall.
