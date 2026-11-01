# Q02: qualification of the three pictured PCBs

Q02 targets the exact E12 ADC characterization board, legacy E14 routed supply and E26 disconnect pilot shown in the README. It does not substitute P02 or a newly repaired E27 for the pictured source files. The separate board audits and any new variants keep their own sources and findings. No fabricated, assembled or powered board has been verified by these tools.

```sh
uv run --locked python -m hardware.qualification.boards.generate
uv run --locked python -m hardware.qualification.boards.check \
  hardware/qualification/boards/generated/capture-template.json --require-pass
```

The empty template must exit **2** with `--require-pass`. Its CSV contains only column headings. No entries, readings, serial numbers, timestamps, instruments or certificates are invented. Old Q01 remains a separate system plan for its original E14/E25/F05 snapshot.

The plan binds actual PCB and schematic hashes, native reports, audit sources and measurement requirements. Changing a limit, deleting a hold, swapping a board or editing a captured plan does not update that binding. Regenerate and independently review the selected source snapshot and fixtures before measuring. Powered qualification stays blocked for a PCB with native opens, DRC or parity findings.

For an attempted case, provide its complete `measurements_csv` artifact: one row per condition and metric, with the exact headings in `measurements-header.csv`. Use numeric values and exact units; each row identifies the instrument and expanded uncertainty in that same unit. Continuous physical measurements require positive uncertainty; exact inspection counts use zero. Unknown acceptance limits stay blocked rather than borrowing full-unit noise/thermal targets or absolute maximum ratings.

The documented project decision rule requires the complete measurement uncertainty interval to fit inside the acceptance interval. An interval entirely outside fails; overlap with a boundary is inconclusive/blocked. Negative rails keep their signs. This is a project rule informed by [ILAC G8 guidance](https://ilac.org/publications-and-resources/ilac-guidance-series/), not a claim of laboratory accreditation or a calculated false-acceptance probability. The uncertainty budget and declared coverage need independent review.

Each attempted case also needs:

- Exact DUT variant, serial, PCB source hash, hashed fabrication package, as-built BOM/part-lot manifest and a source-to-device attestation. Isolated analog and power boards do not require a fictitious firmware image.
- An approved isolated-fixture document bound to this plan and board, including source/current/energy limits, loads, grounding, probe method and numeric settings for every named condition. The plan does not prescribe unreviewed fault-injection energy or approve power-up.
- Actual instrument identities and calibration certificates covering the measurement interval. A nonmetrological inspection method has a hashed reviewed procedure instead of a fabricated calibration certificate.
- Original instrument captures covering all conditions, separate from the summary CSV, with valid SHA-256 hashes. Files and symlinks must stay inside the capture directory.
- Operator, real ordered UTC measurement timestamps and, for continuous measurements, a reviewed expanded-uncertainty budget with coverage factor and coverage probability.

Each numeric metric is bound to an appropriate instrument role; listing an unused DMM does not allow a temperature instrument to supply voltage results. The checker verifies data binding, completeness and comparisons. Production rejects records declared to be synthetic, but changing that label cannot be detected as fraud by a parser: it cannot authenticate physical measurements, certify the uncertainty model, inspect unparsed waveforms or prove which board was manufactured. Existing design failures remain independent holds even if one isolated measurement passes. Its output is an evidence assessment; no result grants fabrication, complete-unit qualification or a power-up release.
