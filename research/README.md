# Research

Investigations that inform the product: reference behavior, component candidates, circuit assumptions and experiments. Notes identify their sources, distinguish observations from assumptions, and link to any resulting design or implementation.

| Note | Purpose |
| --- | --- |
| [Hardware component shortlist](hardware/components.md) | Control, sensor, mechanical and component candidates, source links and unresolved selections |
| [Audio-design history](hardware/audio-design-history.md) | Preserved circuit/converter/gain/noise investigations and historical stage discussion |
| [Reference and fidelity targets](../docs/specifications.md) | Current comparison targets and effect-characterization work still to perform |
| [Hardware design history](../docs/hardware/history/2026-10-23-system-design.md) | Dated system architecture discussion |
| [CAD design history](../docs/hardware/history/2026-10-23-cad-design.md) | Dated dimensions, placement allowances and mechanism notes |

Start a focused investigation from the [note template](note-template.md). Add a topic directory when it has a real note or experiment. Reproduction commands should run from the repository root; put large measurements, renders and temporary results in `build/artifacts/research/`, and retain a checksum or small summary with the note.

Current build/setup instructions live in the [repository guide](../README.md) and the relevant [hardware guide](../hardware/README.md). Verification results live in the [software](../docs/validation.md) and [hardware](../hardware/validation/README.md) validation records. A research note links to the implementation or design decision it informed rather than duplicating its current instructions.
