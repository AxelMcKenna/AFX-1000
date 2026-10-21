# RMX

A native stereo performance effects processor with a portable C++ engine, a hardware-style amber/teal control surface, sample banks, sequencing, and macOS standalone/AU/VST3 adapters. The previous Swift and browser prototypes remain in `Sources/` and `web/`; their [original guide](docs/legacy-prototypes.md) is retained.

## Build the native macOS app

Requires Xcode command line tools, CMake 3.24+, and a C++20 compiler. No downloaded library is required for this app.

```sh
./build-app.sh
open build/RMX.app
```

For a Mac-only rekordbox test, press `Cmd+,`, select **rekordbox — direct app capture**, choose a physical output, and start audio. This needs macOS 14.2+. Direct capture was tested with rekordbox on this Mac; the user confirmed the route worked.

Read the [controls guide](docs/controls.md), [routing instructions](docs/routing.md), and [validation record](docs/validation.md). The effects are original implementations, with sonic matching to the physical RMX-1000 still unverified.

## Build plugins

```sh
cmake -S . -B build-plugins -DCMAKE_BUILD_TYPE=Release -DRMX_BUILD_PLUGINS=ON
cmake --build build-plugins --parallel 4
```

JUCE 8.0.6 is fetched from its official repository. For an existing checkout, add `-DRMX_JUCE_PATH=/absolute/path/to/JUCE`. AU, VST3, and the JUCE standalone are in `build-plugins/RMXPlugin_artefacts/Release/`. The dedicated native app in `build-plugins/RMX.app` provides device-pair selection and direct rekordbox capture. rekordbox does not host these plugins as native rekordbox effects.

For Intel/Apple Silicon universal builds, configure a fresh build directory with `-DCMAKE_OSX_ARCHITECTURES="arm64;x86_64"`. Distribution signing/notarization requires your Apple credentials. Comply with JUCE's applicable license before distributing JUCE-based products.

## Engine checks and rendering

```sh
ctest --test-dir build --output-on-failure
./build/rmx_benchmark
./build/rmx_render input.wav output.wav [preset.rmx]
```

The core builds independently on Linux using the same CMake commands. [Specifications and hardware preparation](docs/specifications.md) separate measured software behavior from analog targets and future hardware work.

## Assets

The factory drums are synthesized by this project. The hardware reference photograph is from [Pioneer DJ's product gallery](https://www.pioneerdj.com/product-images/847/38473749-de98-4b65-aedd-a1c68374c1e4/rmx-1000_1.png); the UI applies a different palette and replaces the visible manufacturer/model badges. That photograph remains a third-party asset, and visual unbranding does not grant redistribution rights. No project-wide distribution license is asserted for the original repository or third-party assets.
