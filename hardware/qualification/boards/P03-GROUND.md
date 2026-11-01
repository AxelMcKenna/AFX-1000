# P03 native ground-transfer investigation

`p03_ground.py` extracts the actual saved AGND polygons, tracks, physical lands and plated-hole geometry. It uses the P03 layer thicknesses and copper depths, finite cylindrical barrel conductance and the complete 160 × 45 mm board extent. The borrowed E28 geometry parser retains its original default board dimensions. This investigation does not assume that all P03 ground points are one ideal node.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m hardware.qualification.boards.p03_ground --steps .4,.2,.1
python -m unittest discover -s tests/tooling -p test_p03_ground.py -v
```

NumPy and SciPy are optional diagnostic dependencies. The three analytical tests compare a rectangular copper sheet with its closed-form resistance, a single barrel with cylindrical-wall conduction, and disconnected layers with no barrel. Passing them checks those numerical building blocks; it does not validate the manufactured board.

Each physical noncapacitive ground pad is a separate unit-current basis electrode with a matching distributed-voltage observation. Multiple physical regions of the same native terminal are retained. Only the front copper of input terminal J101.2 is fixed at zero. Current return through finite barrels to other layers is retained. The solver checks residuals, current balance, dissipated energy and reciprocity. It never adds a fictitious shunt or repairs a disconnected pad numerically.

The declared 85°C material scenario uses trace resistivity 1.8×10⁻⁸ Ωm, barrel resistivity 2.0×10⁻⁸ Ωm and temperature coefficient 0.0041/°C. Barrel depths are scaled to an unaccepted 1.76 mm total-thickness scenario. C50's minimum wall requirement is not a received-board microsection. These are explicit project assumptions, not supplier guarantees. Cell-center rasterization, rectangularized rounded pads, ideal within-layer annuli and uniform electrode distributions remain diagnostic approximations.

The first immutable C50 input is retained in `hardware/validation/board-qualification/generated/p03-ground/687716beaa4a-9cc0cc5d/`, including its PCB, construction and exact used model-source copies. All three grids were unresolved. Refining from 0.4 to 0.2/0.1 mm resolved several small electrodes, but U20.5 remained outside the input-connected mesh. U20.11, U23.5 and retained negative-regulator returns also remained unresolved in the fine grids. No numerical ground-transfer matrix or endpoint-voltage pass was accepted from that snapshot.

Actual ground-return repairs produced a second immutable snapshot, `519e865c3ca6-6a77acfa`, with accepted numerical diagnostics at 0.2/0.1 mm. The fine grid resolves 83 basis electrodes; R303.2 is still unresolved in that snapshot. Residual current balance is below 9×10⁻¹¹ A and reciprocity is checked. As one limited example, a 2.4 A injection at J21 alone produces ideal digital/analog source-ground error contributions of about −0.625/−0.330 mV. Other currents and the external network are excluded from that example; it is not a complete endpoint budget. Subsequent AUX metadata/routing changes invalidate the live-source binding while the exact input/model copies remain available.

The later [a913baa diagnostic](../../validation/board-qualification/generated/p03-ground/a913baaee43e-6a77acfa/verification.json) uses the adopted local feedback corridor and buck input-capacitor repair. Its 0.1 mm grid resolves **all 84 noncapacitive ground electrodes**, including R303.2 and every converter/static-current electrode named in that checkpoint's `dc-current-ports.json`. The 0.2 mm grid still leaves U4.4 unresolved; it must not be described as a complete grid. Fine-grid current-balance residual is below 8.43×10⁻¹¹ A. The exact native board, construction and model sources are preserved alongside the report.

On this later snapshot, the isolated 2.4 A J21 injection contributes approximately −0.784/−0.341 mV to the ideal digital/analog ground-error expressions. This supersedes the earlier example for this copper only. Digital PGND pins U20.9 and U20.11 have different ideal digital-ground coefficients, approximately +0.158 and −0.071 mΩ per ampere. Their real package-current split therefore matters; equal sharing or an ideal common ground cannot be assumed. LT3471 pin5 is the quiet FB2N electrode, while its exposed pad11 is the power ground; the source ledger now distinguishes them. These observations do not supply the missing complete signed currents, external network, convergence bound or physical measurements.

Once connected, the report also provides ideal DC feedback sensitivities at the digital AGND/reference and analog reference/divider points, relative to the actual force-return studs. These expressions are not a substitute for the real regulator/package loops. A complete signed current ledger, external return-network coupling, manufacturing/material uncertainty, mesh convergence and physical Kelvin measurements are still required. Snapshot freshness is reported separately when active routing changes the live PCB. All qualification, fabrication and build-ready flags remain false.

`p03_ground_currents.py` joins a matrix snapshot to the source-bound `dc-current-ports.json`. The board hashes must agree and every ledger source/grid artifact must still match its receipt. Exact used inputs are frozen in the output. Converter currents remain symbolic, while declared local static-current scenarios are shown separately. An unresolved electrode stays unresolved. Multiple package pins produce a coefficient interval for unknown nonnegative sharing fractions, rather than equal sharing; this assumption excludes internal circulating currents and is not a manufacturer current-sharing guarantee. Three portable tests cover signed interval reversal, distinct package-pin coefficients and missing-electrode rejection.

```sh
python -m hardware.qualification.boards.p03_ground_currents \
  --snapshot hardware/validation/board-qualification/generated/p03-ground/a913baaee43e-6a77acfa
python3 -S -m unittest tests.tooling.test_p03_current_terms
```

The default command requires the matching live ledger sources. Later PCB/netlist changes must use matching frozen inputs or a fresh extraction; they cannot be relabeled as this snapshot. Versioned outputs under `signed-current-diagnostic/` retain all five omitted/unclosed current groups from the ledger and do not claim a complete endpoint solution. Each output directory is keyed by every used input hash, so a new ledger/model cannot overwrite earlier captured evidence. A replay from the frozen input tree reproduced both grids and source hashes without the live worktree.
