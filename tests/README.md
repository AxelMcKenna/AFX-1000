# Tests

| Directory | Contents | Run from the repository root |
| --- | --- | --- |
| `core/` | C++ engine, effects, sampler, card and calibration checks | Build with CMake, then run CTest |
| `audio/` | Reference capture, fidelity and noise statistics | `uv run --locked python -m unittest discover -s tests/audio -p 'fidelity_tests.py'` |
| `hardware/` | CAD integration, budget, bypass, carrier and firmware checks | `uv run --locked python -m unittest discover -s tests/hardware -p '*_tests.py'` |
| `packaging/` | Portable release-package checks | `uv run --locked python -m unittest discover -s tests/packaging -p '*_tests.py'` |
| `tooling/` | Board-specific generation, routing and qualification regressions | `uv run --locked python -m unittest discover -s tests/tooling` |

CMake registers the portable audio checks separately. `audio/reference_host_tests.py` is an opt-in integration test requiring a reference host and separately obtained plug-in; see [reference validation](../docs/reference-validation.md). The `a09`, `a10` and `a11` hardware integration suites can also be selected with `-p 'a*_integration_tests.py'`.

See [tools](../tools/README.md) for tool locations and [artifact policy](../docs/artifacts.md) for retained evidence.
