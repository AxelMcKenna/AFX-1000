# Current local software checks

The later [portable checkpoint CI run](generated/portable-handoff-ci/report.json)
passes560 tooling tests:557 passed and three optional skips. It adds42 checks
for FPC01-M1 mounting/copper invariants, the NF05R circuit and the scoped NP01
cross-interpreter verification policy. All451 selected input hashes are identical
before and after the run. This instruments the listed checkpoints, tests and
AP04 inputs; it does not claim every transitive input was instrumented. The
earlier core/firmware checks below remain separately dated evidence.

The [record and logs](generated/current-software-regression/report.json) contain:

- 507 tooling tests: 504 passed and three optional skips.
- A fresh Release core build and all 35 CTest checks run alongside the tooling suite passing.
- 14 targeted fan-monitor, sensor-comparison and coupled-airflow checks passing.
- 12,647 fan-monitor host assertions passing under address/undefined-behavior sanitizers.
- An actual ATtiny84 target build: 1,760 bytes of code and 90 bytes of static data.
- All 2,018 installed AVR toolchain files matching the official compiler archive.

The test and compiler logs are retained. Source hashes were captured after the
runs; the record does not claim a complete before/after hash audit of every input
read during those runs. The CTest run excluded the tooling test because it was
executed separately in full.

The initial 20 tooling failures exposed historical records pointing at changed
working files. Their [source audit](../../cad/a12/qualification_reviews/historical_sources/README.md)
preserves exact old bytes where available and explicitly marks two unrecovered
historical files. Passing tests does not make those packets current or complete.
Live-input checks in new native validators remain strict.

These results verify software behavior and local build/regression checks within
their stated scope. The MCU has not been programmed or exercised. Interrupt and
ADC timing, worst-case runtime stack, electrical integration, latest combined
CAD, startup/fault behavior, airflow, temperatures and physical board tests
remain unfinished. All physical and fabrication-release flags remain false.
