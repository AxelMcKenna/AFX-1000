# Performance and hardware targets

## Reference and targets

Pioneer's [published RMX-1000 specifications](https://forums.pioneerdj.com/hc/en-us/articles/204673769-PIONEER-ANNOUNCES-THE-NEW-RMX-1000-REMIX-STATION) list 48 kHz sampling, 24-bit converters, 20 Hz–20 kHz response, 0.005% maximum THD, 20 dB headroom, and S/N of 102 dB in send/return or 98 dB in master mode.

| Area | Project implementation or target | Evidence/status |
| --- | --- | --- |
| Processing rate | 44.1 / 48 / 88.2 / 96 kHz | Engine checks cover all four; live Mac route ran at 44.1 kHz. |
| Arithmetic | Stereo floating-point DSP | Implemented. Not a claim about physical converter resolution. |
| Audio callback | No allocation, locks, file I/O, or UI work | Allocation test covers processing, variable block sizes, sample roll, and band roll. |
| Live buffer | 64–128 frames where supported | Native buffer selector; hardware may choose a different actual size. |
| DSP deadline | p99 below 50% at 48 kHz / 128 frames | Benchmark executable reports each Scene FX. Full live-device latency is separate. |
| Neutral response | Preserve stereo samples within floating-point rounding error | Neutral and wet-only null checks. |
| Analog noise / distortion / headroom | At least the reference specs; prefer ≥110 dB S/N and ≤0.003% THD for future converters | Requires interface/PCB selection, gain calibration, and measurement. Not established by this software build. |
| Long-session reliability | Two hours with rekordbox, active controls, no sustained dropouts | Still needs a live soak test on the intended setup. |
| Sonic matching | Compare effect responses against reference recordings | Not performed. Current effects are original approximations. |

## Hardware architecture

The C++ engine takes planar float audio, a sample rate, timestamped pad events, transport information, and stable parameter IDs. It does not depend on JUCE, Cocoa, Core Audio, a filesystem, or a display. A future embedded adapter supplies audio buffers and control events; the preset schema and MIDI mappings remain shared.

The Linux CI configuration builds the headless core on x86-64 and ARM64. A real ARM hardware benchmark and round-trip latency measurement remain required. The desktop process-tap route is an Apple adapter, not part of the portable engine.

A future standalone unit needs stereo line ADC/DAC, calibrated master/send-return gain ranges, physical controls, storage, a watchdog, and a physical bypass path. Select the board, codecs, power design, and RAM only after profiling the chosen sample-bank limits and worst effect combination. A USB/MIDI controller can precede that unit and use the existing parameter IDs.

## Fidelity checks to complete

Record dry and processed output from the real unit at fixed gain, tempo, knob positions, and input signal. Compare delay spacing/feedback decay, filter response, reverb decay, spiral pitch trajectories, band isolation, sample pitch, quantization, and release timing. Match loudness before listening. Keep these recordings separate from project-owned factory samples.
