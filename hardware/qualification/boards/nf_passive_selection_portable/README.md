# NP01-P1 — bounded portable replay

This is a verification successor to the immutable55-file NP01 packet, seal `bce8bfb8154395f2480742a1f37f3ecccc29d9fef96cdbb40567a20e4067845a`. No NP01 source, result, table, qualification flag or seal was edited. Its original strict Python3.12 test failures remain recorded as failures.

The original run used `/usr/bin/python3` **3.9.6**. Independent review used `.venv/bin/python` **3.12.13**. Python3.12 changed float `sum` accuracy. Exact cross-runtime replay found **23 changed scalars**, all five-term `total_fraction` sums, each **one adjacent binary64 step**. The largest difference is6.938893903907228×10⁻¹⁸ in fractional resistance. All component identities, summands, source hashes, body/land dimensions, booleans, monitor results, DC power screens and other model values agree exactly. This is a numerical replay issue; no component receiving allowance is widened.

`policy.py` allows at most **four adjacent binary64 steps**, solely for the explicitly enumerated five-term totals. For five nonnegative terms, ordinary left-to-right summation has four rounded additions; a four-step cap conservatively covers their rounding accumulation. The observed difference is one step. Additionally, both stored and replayed totals must lie within that cap of the exact rational sum of the five **unchanged** binary64 summands, correctly rounded back to binary64. Missing/negative/nonfinite/changed terms fail. The policy never rounds or permits changes to source inputs, dimensions, hashes, strings, counts, flags or other numerical paths. Decisions such as `complete_0p5pct_planning_met` remain exact booleans.

The new verifier checks all55 original sealed files before and after replay. It reruns the complete selection, life, monitor and DC-power payloads from captured inputs. It runs the old artifact checks as well; only the known legacy exact-life-sum mismatch can be superseded, and only after the whole new comparison passes. Unknown missing/changed artifact or geometry errors still fail. No other legacy evidence error is suppressed.

`diagnostics/original-strict-python39.log` records the original13 tests passing. `original-strict-python312.log` records the two actual strict failures. The two initial diagnostic portable reports predate an import-order-only formatting fix; their exact historical `verify.py` is preserved in `diagnostics/historical-code/`. They are historical diagnostics. The source-current reports and explicit return codes are in `final-runs/`.

There are **23 successor tests** under each runtime: all11 unaffected NP01 tests plus12 policy tests. The replacements preserve saved artifact/hash checks and captured replay with the bounded sum policy. Mutations reject a five-step sum, a material drift change, even a one-step altered summand or body dimension, a source hash change, missing entries, nonfinite values and promoted qualification flags. The exact rational reference is checked independently. The raw old Python3.12 failures remain; they are not relabeled as passes.

Run the successor without editing the historical packet:

```sh
python3 -m hardware.qualification.boards.nf_passive_selection_portable.verify
.venv/bin/python -m hardware.qualification.boards.nf_passive_selection_portable.verify
python3 -m unittest hardware.qualification.boards.nf_passive_selection_portable.test_portable
.venv/bin/python -m unittest hardware.qualification.boards.nf_passive_selection_portable.test_portable
```

`run_suite.py --output NEW_DIRECTORY` captures six actual subprocess statuses/logs under both installed interpreters and refuses an existing directory. The legacy3.12 run is expected to fail with the two preserved exact-float tests; both successor suites and verifiers must return0. No electrical, physical, fabrication or release qualification is asserted.

Primary runtime reference: [Python3.12 built-in sum change](https://docs.python.org/3.12/library/functions.html#sum). The actual captured runtime/model differences, exact rational checks and mutation results are the evidence here.
