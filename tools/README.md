# Development tools

Run Python tools from the repository root with `uv run --locked python -m <module>`. For example:

```sh
uv run --locked python -m tools.audio.common.fidelity --help
uv run --locked python -m tools.packaging.package_macos --help
```

| Directory | Contents |
| --- | --- |
| `audio/common/` | Reference capture, fidelity scoring, factory matching and WAV comparison |
| `audio/drums/` | Drum identification, playback, controls and performance audits |
| `audio/noise/` | Noise statistics, modulation, sidechain and streaming audits |
| `audio/reverb/` | Reverb Up/Down measurements, models and audits |
| `audio/spiral/` | Spiral models, captures and compatibility checks |
| `audio/filters/` | Filter/Crush Echo, Isolate, Cut/Add, Trans/Roll and scene routing |
| `audio/release/` | Release FX matching and compatibility |
| `audio/performance/` | Combined performance-path capture and delivery checks |
| `probes/` | C++ diagnostic executables, built through root CMake targets |
| `hosts/` | Offline reference plug-in host and format adapters |
| `cli/` | Renderer, card exporter, benchmarks, memory checks and sound preview |
| `assets/` | Panel and README artwork generators |
| `packaging/` | macOS release packaging |
| `artifacts/` | Recovery of archived release bundles |

The hardware generation, board-check and firmware setup scripts at this level retain their established paths because hardware review records bind their source hashes. Board-specific tools live with their owning designs under `hardware/`.

The [path migration index](../docs/path-migrations.json) maps former paths to current locations. Historical measurement records retain their original paths and hashes; relocating current code does not revalidate those measurements.
