# Signal PCB completion

The [latest routing project](native-routes-15/signal_main.kicad_pro) has **125 open connections**. A_C504 and A_C516 now connect over analog ground in the right output stage. KiCad reports zero geometry and ERC findings. A_U201 still needs the ES9292QPRO footprint. [Latest routing review](native-routes-15/README.md)

## Assembly workflow checkpoint 02

The routing candidate selected by the assembly workflow is `native-routes-02/signal_main.kicad_pro`.
It adds 19 joins to r148, reducing native opens from 162 to **143**. Relative
to the selected r139 board, this also carries the verified PD_R repair in r148.
This is an intermediate checkpoint toward completing the signal PCB; it is
**not a fabrication release**. All 169 configured compatibility checks pass, and the candidate is selected
in the assembly workflow. This selection does not release fabrication.

The new routes cover ADC left input, processor input, bypass input/output and
output coupling/series nodes. `routes-02/routing.json` records exact nets,
points, segment identities and sources. All additions are 0.2 mm F.Cu tracks;
no new via, footprint move, drill, plane edit or rule exception is introduced.
The second pass completes `/A_BYPASS/IN_R`: A_J607 pin 3, A_K601 pin 7
and A_K602 pin 5 share one verified native connectivity group.

## Observed verification

- Pinned Linux KiCad 10.0.7: 143 uncapped opens, zero geometry findings,
  zero ERC findings, identical schematic net partitions. The missing
  A_U201 ES9292QPRO footprint warning remains explicit.
- All 7,773 existing UUID-bearing board objects and original physical
  connectivity are preserved. Direct native-file review additionally
  verifies board-global settings and every saved zone fill exactly.
- Nineteen actual-native-copper reference cases pass. New copper uses
  connected adjacent ground fields. Existing same-net transition holes are
  accounted separately under the r148 policy; none are added or enlarged.
- A fresh native capture independently sums pad-cluster gaps to 143.
- Forty assembly-workflow and mechanical-freshness regressions pass after selection.
- Acceptance regressions reject missing references, changed fills, altered
  stack settings, incorrect open counts, wrong nets, extra copper and
  duplicate copper identities and stale shared dependencies; the positive frozen checkpoint is exercised. Two additional regressions
  verify the receiving-pad connection and reject selection of a different board
  in the same native directory. CI audits the actual selected signal board.
- The assembly freshness comparison finds no mechanical differences in
  all 477 signal and 1,101 power footprint records. All 169 configured assembly checks pass
  against `assembly-candidate-02.json`, with the complete input snapshot verified
  before selection. `assembly-results-02.json` records the native run.

`routes-02-review.json` binds the current routing/reference acceptance.
`source-inputs.json` freezes the verifier and shared dependencies; stale inputs
fail acceptance. Earlier checkpoint reports retain their original revision scope.
`integration-review-02.json` binds the selected 143-open PCB, capture and all
169 assembly checks. `selected-assembly-results-02.json` verifies the active selection.
`capture-routes-03/capture.json` is the portable native input for the next
routing pass. Superseded local experiments are retained under the ignored
`experiments/` directory and are not selected artifacts.

## Reproduce

From the repository root, using its locked Python environment:

```sh
python -m unittest hardware.cad.signal_completion.test_review hardware.cad.signal_completion.test_bypass_connectivity
python -m hardware.cad.signal_completion.verify_selected /path/inside/this/checkout/selected-review.json
python -m hardware.cad.signal_completion.review_routes \
  hardware/cad/signal_completion/routes-02 \
  hardware/cad/signal_completion/native-routes-02 \
  /path/inside/this/checkout/new-review.json
```

Use a new report path; evidence is never overwritten. The planner and native
verifier likewise require new output directories. `verify_native.py` runs only
inside the pinned isolated Linux KiCad workflow used by the preceding board
checkpoints. No host CAD runtime is used.

## Remaining completion work

The 143 existing opens span 96 nets. Continue from the fresh native capture,
prioritizing bounded LED escapes, ADC reference/bias/monitor paths, remaining
bypass/output paths and the two-board digital/audio interfaces. Any new via
requires explicit return-path proof and a retained-reference audit after native
refill; the surface-only acceptance shortcut cannot approve a via candidate.

A_U201 is still unplaced. The [official ESS v0.1 datasheet](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf)
confirms pin identities but lacks the required revisioned package/land/stencil
dimensions, as recorded in `hardware/electronics/converter/package_review/`.
Obtain those inputs before creating or placing a production footprint. A
nominal generic 48-QFN does not close this requirement.

Zero routing opens alone will not complete fabrication acceptance: finish the
codec's actual placement and all associated connections, review the complete
analog force/sense loops and references, resolve the nominal 0.02 mm D101/C105
receiving gap with actual manufacturing tolerances, and accept the stack,
BOM/lands and manufacturing outputs. Physical operation remains unmeasured.
