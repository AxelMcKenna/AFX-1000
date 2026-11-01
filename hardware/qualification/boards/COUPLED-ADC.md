# E12-R2 coupled analog simulation investigation

`coupled_adc.py` adds the actual left-channel OPA1656 buffer, OPA4192 reference buffer and common-mode servo to the existing THS4551 driver-stage model. Native R7–R13/C6–C7 values and op-amp pin connections come from the frozen R2 netlist. This is separate evidence; it does not modify or replace the earlier R2 stage-only receipt.

Three unmodified external manufacturer libraries are checked by exact SHA256: [THS4551 Rev B](https://www.ti.com/lit/zip/sbomb92b), [OPAx192 Rev F](https://www.ti.com/lit/zip/sbom862f) and [OPA1656 Rev C](https://www.ti.com/lit/zip/sbomaw6c). The libraries are not redistributed. Use the native ngspice shared library and matching XSPICE code models, with these paths supplied explicitly:

```sh
python3 -m hardware.qualification.boards.coupled_adc \
  --library /external/libngspice \
  --code-models /external/ngspice-code-models \
  --ths4551 /external/ths4551.lib \
  --opa192 /external/OPAx192.LIB \
  --opa1656 /external/OPA1656.LIB
```

Five initial scenarios are retained in `hardware/validation/board-qualification/generated/r2-coupled/`: signal transfer, converter-reference transfer, ±10% servo capacitor cases, and a zero-start DC input sweep. **All five require dynamic gmin stepping and are rejected for numerical comparison under the existing strict solver-cleanliness rule.** Completion of an assisted solve is not recorded as a pass. The reported numeric vectors and summaries are diagnostic only. The receipt explicitly reports zero accepted cases and binds source, deck, raw output/log and external-model hashes.

Add `--model-controls` to run isolated controls in separate solver processes with a 30-second compute budget per circuit. The existing THS4551 stage control is solver-clean. The OPA1656 unity follower needs convergence assistance, and the OPAx192 unity follower fails dynamic gmin/true gmin/source stepping and does not finish its transient operating-point fallback within the budget; that worker is terminated and recorded as rejected. Decks, live solver logs, results, exit codes and hashes are retained separately in `generated/r2-coupled-model-controls/`. This localizes a model/solver compatibility or initialization investigation; it does not diagnose physical instability of either op-amp or the ADC board. A supported-solver or independently checked alternate manufacturer-model comparison is required before relying on the coupled numeric results.

Increasing nominal-case operating-point iterations to 500 did not eliminate stepping in an exploratory run. A second exploratory nominal-case run with guessed external node voltages failed to find an operating point. Those observations are not proof of physical instability, a unique equilibrium, a model defect or a board fault. Further investigation needs isolated manufacturer model controls, supported-solver comparison and a reviewed operating-point/complete-load model; guessed startup states must not substitute for power-sequence verification.

`adc_model_compare.py` adds four separately bounded controls with the official unmodified [OPAx192 TINA model](https://www.ti.com/lit/zip/sbom860e), [OPA1656 TINA model](https://www.ti.com/lit/zip/sbomaw8), and the original OPAx192 PSpice model. Supply, input and 2 kΩ output load remain identical to the initial controls. Both OPAx192 variants also have a separately named 1 mΩ series-feedback hypothesis, which is not an extracted board trace. The TINA OPAx192 ideal-feedback control times out; its finite-feedback control completes with solver assistance, as does the PSpice counterpart. The TINA OPA1656 follower also needs assistance. **Zero of these four controls qualify for numerical comparison.** The change in completion behavior supports further initialization/interoperability investigation rather than any inference about physical oscillation. Sources, model hashes, complete decks, live logs, raw vectors, timeouts and worker exit codes are in `generated/r2-model-comparison/`.

Reproduce with `python3 -m hardware.qualification.boards.adc_model_compare`, supplying `--library`, `--code-models`, `--opa192-tina`, `--opa1656-tina`, and `--opa192-pspice` as external paths. The exact accepted model hashes are in the script and receipt. Each control uses a fresh solver process and a 30-second compute budget. Changing model versions or adding artificial circuit elements to obtain convergence requires a separate reviewed experiment; it must not overwrite the frozen R2 native or stage-only evidence.

The sources remain ideal ±12 V, 5 V, negative bias and 3.3 V reference. Converter loading is the declared static 260 Ω per-pin-to-1.65 V hypothesis. The real ESS DC/switched input and reference behavior are unavailable. Diode-clamp conduction/capacitance, pump/bias-monitor/PD sequences, extracted board parasitics and shared-package/supply behavior are omitted. This expands the coupled circuit under investigation; it does not establish return ratio, phase margin, noise, clipping, THD, partial-power safety or full-board stability. All physical and fabrication release flags remain false.
