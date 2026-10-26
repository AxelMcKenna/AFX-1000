# Research

Investigations that inform the product: reference behavior, component candidates, circuit assumptions and experiments. Notes identify their sources, distinguish observations from assumptions, and link to any resulting design or implementation.

| Note | Purpose |
| --- | --- |
| [RMX-1000 sound matching](audio/rmx1000-fidelity.md) | Primary-source findings, DSP gap review, reference capture plan and proposed fidelity acceptance criteria |
| [Factory 48 kHz measurements](audio/measurements/2026-10-26-factory-48k.json) | Original plug-in provenance, fitted Isolator/Echo findings and independent per-case waveform errors |
| [Noise filter identification](audio/measurements/2026-10-26-noise-filter.json) | Common-seed output identification, coefficient calibration and excluded-position transfer checks |
| [Noise statistical validation](audio/measurements/2026-10-26-noise-validation-48k.json) | Long stereo renders, per-channel band/level equivalence intervals and capture provenance |
| [Clock and tempo measurements](audio/measurements/2026-10-26-clock-48k.json) | Whole-millisecond beat periods, Auto/manual behavior and additional-tempo impulse checks |
| [Filter Echo identification](audio/measurements/2026-10-26-filter-identification.json) | Public I/O fits for BPF/HPF/LPF direct filters, coefficient maps and response errors |
| [Filter Echo validation](audio/measurements/2026-10-26-filter-validation-48k.json) | Independent stereo signals, crossfaded delay taps, 137 BPM and native button-off tails |
| [Crush identification](audio/measurements/2026-10-26-crush-identification.json) | Sample-hold arithmetic, resonant filtering, DC steps and first-host-block diagnostics |
| [Crush validation](audio/measurements/2026-10-26-crush-validation-48k.json) | Independent stereo signals, 90/128/137 BPM, late clock boundaries and native button-off tails |
| [Spiral characterization](audio/measurements/2026-10-26-spiral-identification.json) | Determinism, non-additivity, channel coupling, onset and pitch diagnostics; generator remains unmatched |
| [Spiral return component](audio/measurements/2026-10-26-spiral-return-validation-48k.json) | Four-comb return validation using measured original pitch fixtures; explicitly excludes full-effect matching |
| [Spiral core investigation](audio/spiral-core.md) | Linked peak/activity measurements, stepped release, neutral-clock reversals and a 361-render sweep retaining 76 full-model failures |
| [Spiral robustness audit](audio/measurements/2026-10-27-spiral-robustness-audit.json) | Original one-ULP sensitivity, quiet scaling, conditioned recurrence and rejected prospective feedback-timing predictions; waveform gate unchanged |
| [Reverb identification](audio/measurements/2026-10-27-reverb-identification.json) | 88 verified captures, Main-dependent timing, long Sub1 decay and independently checked output-filter component |
| [Reverb production baseline](audio/measurements/2026-10-27-reverb-production-baseline-48k.json) | All 52 active non-silent complete renders fail; Main-zero/silence passes are distinguished explicitly |
| [Reverb Down network prototype](audio/measurements/2026-10-27-reverb-down-network-prototype-48k.json) | Autonomous five-pair comb candidate passes 28 complete neutral-setting renders, including eight prospective captures; full control maps remain unfinished |
| [Reverb Down static control maps](audio/measurements/2026-10-27-reverb-down-control-interaction-prototype-48k.json) | 1,204 complete renders pass, including 64 fresh mixed cases; measured timing and a wet-level interaction extend the research candidate beyond neutral controls |
| [Rejected separable level map](audio/measurements/2026-10-27-reverb-down-control-separable-prototype-48k.json) | Retains all 14 mixed-control failures that required the additional interaction sweeps |
| [Reverb Down motion investigation](audio/measurements/2026-10-27-reverb-down-motion-characterization.json) | 61 verified original recordings, preserved tails, separate control timing and a 26/61 first candidate with all failures retained |
| [Reverb Down cutoff motion](audio/reverb-down-motion.md) | Sub2 slew passes 16 cutoff-motion cases, including eight fresh captures; complete stateful candidate is 42/69 with 27 failures retained |
| [Reverb Down slow-state measurements](audio/measurements/2026-10-27-reverb-down-state-density-characterization.json) | 93 additional original captures isolate dry ramps, button startup and slow wet-control changes; gain-only and simple coefficient-ramp fixes remain rejected |
| [Reverb Down Sub1 motion](audio/measurements/2026-10-27-reverb-down-sub1-motion-validation-48k.json) | Staged Sub1 clock passes 14 motion cases including eight fresh captures; complete candidate is 56/77 with 21 Main/button/combined failures retained |
| [Reverb Down activation state](audio/measurements/2026-10-27-reverb-down-activation-validation-48k.json) | 98/113 complete renders pass, including eight fresh activation cases; Main/combined and immediate-input initialization failures remain explicit |
| [Reverb Down adaptive Main](audio/reverb-down-motion.md) | 126/129 complete renders pass, including eight fresh Main programs after active initialization; pre-activation timing and immediate-input failures remain explicit |
| [Reverb Down callback/startup](audio/reverb-down-motion.md) | 176/176 complete renders pass, including eight fresh startup programs; 49 non-silent pre-wet dry prefixes match numerically, with signed-zero precision corrected in the current audit |
| [Reverb Down bounded processor](audio/measurements/2026-10-27-reverb-down-production-validation-48k.json) | 184/184 renders pass, with 176 byte-identical regressions and eight fresh large-callback programs; bounded buffers and allocation/sanitizer checks pass, live Engine integration remains unfinished |
| [Reverb Down live Engine](audio/measurements/2026-10-27-reverb-down-engine-validation-48k.json) | 192/192 complete Engine renders pass, including eight fresh programs; native routing/resources, AU/VST3 audio and latency checks pass within their stated scopes |
| [Reverb Up neutral network](audio/reverb-up.md) | Autonomous research renderer passes 28 static Main128/Sub1-128 cases, including eight new recordings; identifies Up's input band-pass and filtered feedback, with live Up/maps/motion unfinished |
| [How reference audio checks work](audio/reference-method.md) | Original plug-in A/B setup, signal design, frozen predictions, waveform gates, failure retention and reproduction |
| [Hardware component shortlist](hardware/components.md) | Control, sensor, mechanical and component candidates, source links and unresolved selections |
| [Audio-design history](hardware/audio-design-history.md) | Preserved circuit/converter/gain/noise investigations and historical stage discussion |
| [Reference and fidelity targets](../docs/specifications.md) | Current comparison targets and effect-characterization work still to perform |
| [Hardware design history](../docs/hardware/history/2026-10-23-system-design.md) | Dated system architecture discussion |
| [CAD design history](../docs/hardware/history/2026-10-23-cad-design.md) | Dated dimensions, placement allowances and mechanism notes |

Start a focused investigation from the [note template](note-template.md). Add a topic directory when it has a real note or experiment. Reproduction commands should run from the repository root; put large measurements, renders and temporary results in `build/artifacts/research/`, and retain a checksum or small summary with the note.

Current build/setup instructions live in the [repository guide](../README.md) and the relevant [hardware guide](../hardware/README.md). Verification results live in the [software](../docs/validation.md) and [hardware](../hardware/validation/README.md) validation records. A research note links to the implementation or design decision it informed rather than duplicating its current instructions.
