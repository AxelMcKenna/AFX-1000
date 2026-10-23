# Tests

| Directory | Ownership |
| --- | --- |
| `core/` | DSP, engine state and real-time queue/snapshot behavior |
| `controls/` | Shared panel actions, MIDI and hardware control mappings |
| `app/` | Session workflows and device-buffer calculations |
| `macos/` | Native controller and platform workflows |
| `plugin/` | JUCE processor state, sample ownership and callback regressions |
| `firmware/` | Embedded policies, converter protocols, memory arena and wire formats |
| `tooling/` | Python EDA, CAD and artifact-tool checks |
| `support/` | Shared test assertions |

Registration lives in [CMakeLists.txt](CMakeLists.txt). Executable names and their locations under the build root remain stable for the firmware verifier. Run `ctest --test-dir build --output-on-failure` from the repository root, or run Python checks with `python3 -m unittest discover -s tests/tooling -p 'test_*.py'`. CAD tests skip when their optional mesh dependencies are unavailable.
