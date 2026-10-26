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
| [Hardware component shortlist](hardware/components.md) | Control, sensor, mechanical and component candidates, source links and unresolved selections |
| [Audio-design history](hardware/audio-design-history.md) | Preserved circuit/converter/gain/noise investigations and historical stage discussion |
| [Reference and fidelity targets](../docs/specifications.md) | Current comparison targets and effect-characterization work still to perform |
| [Hardware design history](../docs/hardware/history/2026-10-23-system-design.md) | Dated system architecture discussion |
| [CAD design history](../docs/hardware/history/2026-10-23-cad-design.md) | Dated dimensions, placement allowances and mechanism notes |

Start a focused investigation from the [note template](note-template.md). Add a topic directory when it has a real note or experiment. Reproduction commands should run from the repository root; put large measurements, renders and temporary results in `build/artifacts/research/`, and retain a checksum or small summary with the note.

Current build/setup instructions live in the [repository guide](../README.md) and the relevant [hardware guide](../hardware/README.md). Verification results live in the [software](../docs/validation.md) and [hardware](../hardware/validation/README.md) validation records. A research note links to the implementation or design decision it informed rather than duplicating its current instructions.
