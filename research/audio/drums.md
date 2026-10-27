# Factory drum sound matching

27 October 2026. The user has prioritized the factory **kick, snare, clap and hi-hat** ahead of the remaining effects. The current [`FactoryDrums.h`](../../include/rmx/FactoryDrums.h) generates project voicings; none of the four is yet reference-matched. The existing sampler tests verify behaviour, not resemblance to the original sounds.

## First reference campaign

The [24-case original characterization](measurements/2026-10-27-drum-original-characterization.json) uses RMX-1000 Plug-in 2.2.0, factory Default, stereo48k/120BPM, silent input, neutral pitch raw128 and level raw128. Each instrument has a baseline, fresh-instance repeat, callback32/callback256 repeats, a declared 37-frame trigger shift, and rapid retriggers. Baselines use callback128 and three separated hits. Original binaries and audio stay under ignored build artifacts; the report contains hashes and numeric observations.

[`rmx_drums.py`](../../tools/rmx_drums.py) checks exact plans, silent samples, callback/extent, receipt and auxiliary hashes, immediate/final parameter readbacks and the saved matrix before analysis. This is discovery, not a candidate holdout or a sound-match claim. No gain or alignment is fitted.

All four instruments are mono in the checked stereo outputs. Their three separated hits are bit-identical, as are fresh-instance and 32/128/256 callback repeats. Repeatability alone does not distinguish stored playback from deterministic synthesis.

| Instrument | First nonzero output after block-aligned trigger | Last nonzero delta, threshold1e-12 | Peak at raw128 level |
| --- | ---: | ---: | ---: |
| Kick | 48 frames | 25,567 frames | 0.707622 |
| Snare | 48 frames | 22,415 frames | 0.691373 |
| Clap | 32 frames | 60,655 frames | 0.602424 |
| Hi-hat | 48 frames | 14,290 frames | 0.727877 |

The declared 37-frame trigger shift moves the first output by 32 frames: onset delta becomes43 for kick/snare/hat and27 for clap. This exposes block/control timing, rather than just a freely shiftable sample waveform. Source changes and callback fragments must be modeled causally; an alignment search must not hide them.

The [first attempted retrigger models](measurements/2026-10-27-drum-retrigger-first-probe.json), using an original isolated hit as a component fixture, reject both unrestricted additive overlap and immediate single-voice restart under a naive floor32 event mapping. Relative errors exceed 100% for every instrument. This does not establish polyphony or a reset rule: partial-callback emission and trigger timing need to be accounted for before interpreting that result. It is not independent candidate sound validation.

## Reproduce and next work

```sh
uv run --locked python -m tools.rmx_drums capture \
  --host /path/to/Intel/RMXReferenceHost \
  --plugin /path/to/RMX-1000Plug-in.vst --session build/new-drum-session
uv run --locked python -m tools.rmx_drums analyze \
  --session build/new-drum-session --report build/new-drum-characterization.json
```

All destinations must be new. Next compare the actual Engine's existing drum output, quantify the kick's attack/body/decay mismatch, identify its pitch/envelope structure, and test revised hypotheses on new recordings. Pitch/level laws, alternate decay/envelope settings, rolls, overlapping instruments, retriggering and broader rates/profiles remain required. No drum accuracy percentage has been established.
