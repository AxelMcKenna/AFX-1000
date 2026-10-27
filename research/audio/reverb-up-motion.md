# Reverb Up control motion

27 October 2026. Factory Default Up, stereo 48 kHz, 120 BPM. This extends the [accepted static research maps](reverb-up.md). The live Engine's Up processor is still approximate; full-device 99% fidelity remains unfinished.

## Discovery checkpoint

The [first independent motion candidate](measurements/2026-10-27-reverb-up-motion-first-prototype-48k.json) passes **47/69** complete discovery comparisons. This is development evidence, not a new prospective holdout. All static baselines and button-change cases pass, as do the tested cutoff steps/ramps/repeats. Main motion, Sub1 increases and several cold-input combinations still fail; every failed waveform/window is retained.

The 69 [original captures](measurements/2026-10-27-reverb-up-motion-original-characterization.json) include twelve button cases, thirty-one step/baseline cases, twelve ramp/baseline cases, six callback repeats, and eight cold-input cases. Sources and gestures intentionally reuse the earlier Down investigation's diagnostic recipes to isolate the difference between effects. They do not reuse Down output as the Up reference. Each original render selects `ReverbUpButton`, factory Default, and its declared controls; exact source samples, receipt/auxiliary hashes, initial/event/final readbacks, tempo, extent and callback size are checked.

All six 32/256-frame callback repeats are bit-identical to their corresponding 128-frame original captures. Cutoff changes first affect raw original output at frame192064 for an event requested at192037, consistent with the existing 32-frame internal boundary. This constrains timing; it does not prove the complete Up control state machine.

## Initial candidate and what remains uncertain

The [research processor](experiments/ReverbUpMotion.cpp) uses Up's measured five-pair network, explicit observed feedback high-pass coefficients, static delay/level maps, Main-dependent input band-pass and Sub2 high-pass. The [fixture](experiments/reverb_up_motion_probe.cpp) supplies declared callback/event boundaries and a separate predicted dry trace. Nothing calls the original DSP from the candidate.

The first timing hypothesis reuses independently implemented Down rules: 32-frame audio buffering, one raw cutoff step per block, staged Sub1 feedback updates, adaptive Main geometry clock, input/button fades and muted startup. Up's dry gain stays unity. Main input-filter coefficients initially interpolate alongside the slow geometry; this is a hypothesis, not a measured transient filter law. Large Main-motion errors reject the complete first hypothesis even where its static endpoints agree.

A [read-only scalar observation](measurements/2026-10-27-reverb-up-motion-static-state-observation.json) confirms the original's Main128 input band-pass coefficients, return level, initial Main period and one fractional delay. The debugger-rendered original WAV and plan hashes match the existing reference exactly. No original code, instruction listing or raw debugger artifacts are distributed. An empirical return-level expression consistent with these observations and the static maps is `0.7*(a + min(1,Main/183)^2*(1-a)^3)`, where `a=1` through Sub1-127, otherwise `a=0.65+0.35*((255-Sub1)/128)^2`. One-point state observation and static-map agreement do not validate its moving-state update order.

## Fixed acceptance and reproduction

The comparator crops **32 frames from both original and candidate** and fits neither comparison gain nor wet alignment. Whole output, predicted-dry-subtracted wet output, post-input tail, windows around every event, and declared startup windows must each pass the same per-channel 1% relative RMS limit. Reference summed energy at most `1e-20` switches to an absolute RMS limit of `1e-8`. A candidate-predicted dry trace subtracted from both sides is diagnostic, not an independently captured wet stem. Main remains rejected even where a whole-output average hides a wet/window failure.

```sh
cmake -S . -B build/reverb-up-motion -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=OFF -DRMX_BUILD_REFERENCE_HOST=OFF
cmake --build build/reverb-up-motion --target rmx_reverb_up_motion_probe
uv run --locked python -m tools.rmx_reverb_up_motion --help
```

Use `capture --stage button|steps|ramps|blocks|cold` separately with the original Intel host/plug-in, static model, reviewed calibration and a new session directory. These stages are explicitly discovery captures. `characterize --session STAGE DIRECTORY` checks recipes/readbacks and original baseline differences. `compare --session STAGE DIRECTORY` takes the research renderer, same static model/calibration and a new output directory; repeat the session argument for the five stages. Reports and WAV destinations must be new. Historical source/renderer hashes require their recorded Git checkpoints.

Next resolve Up's moving input filter, Main geometry and Sub1 level clocks from independent original measurements, then freeze a revised candidate before different fresh source/control captures. Startup, bounded-resource qualification and live Engine integration remain required; this checkpoint does not claim them.
