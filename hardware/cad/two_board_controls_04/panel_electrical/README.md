# Panel electrical checkpoint

Open `assembly/panel.kicad_pro` in KiCad 10. The 39-page hierarchy explicitly instantiates 34 passive carrier PCBs, 3 directly wired SA36-11YWA digits, 29 B3F-1000 button contacts, 10 potentiometers, and the existing signal-board header boundary. It covers all 96 existing lighting sinks. Boundary symbols do not represent extra physical connectors. The two main boards and separate sensor PCB are outside the 34-carrier count.

`layouts/` contains 12 independently specified local schematics. Every component value, footprint and electrical pin group matches its unchanged carrier PCB. `assembly-manifest.json` maps unique assembly references back to local PCB references; it preserves each local circuit when mapping its external solder pads into the panel. `contracts.py` defines intended circuits independently of PCB extraction. No CAD or PCB geometry changes in this checkpoint.

Native KiCad 10.0.7 runs use the pinned isolated Linux image `kicad/kicad@sha256:c8f05703e865a1caa7266851cf4986dd01d5fb1148e4f63382b6a73466ba7e71`, network disabled, read-only root, 2 CPUs and 2 GB. `native-r2/` records zero severity-all ERC findings and native exported-netlist parity for all 12 layouts. `assembly-native-r3/` is the final whole-panel verification; earlier assembly runs are historical. `native-r1/` retains initial off-grid findings. Visual self-review corrected tall connector overlap and left-facing global label orientation before the final run.

Run `generate.py`, `panel.py`, then `seal.py` with Python from the repository environment. `seal.py` verifies deterministic regeneration and binds the complete generator, footprint, native main-board, wiring CSV and channel-function inputs. In the isolated image, run `native.py OUTDIR` and `assembly_native.py OUTDIR` in fresh output directories. Run `verify_panel.py ASSEMBLY_OUTPUT_DIRECTORY` on the exported netlist. Its independent checks trace each channel by intended function through the actual emitter/display pins, all 24 RGB resistor branches, five selector states, 29 button contacts and ten pot terminal maps. Five injected faults must fail: reversed LED, wrong display segment, broken ring branch, missing selector ground and incorrect pot wiper.

## Source-bound control behavior

`reference/panel-contract.json` is frozen from installation package commit `9567906e` (SHA256 `5a98630e65a4b929d7564e61fbd277ca62d5e057cb87169dacedd7b563cd9374`). `reference/button-contact-contract.json` supplements its obsolete pending button field (SHA256 `a1fc74c1e45c9d7fb277f5f5ebf285e343b83f58a70eded6261138f91438462f`). The originating package retains manufacturer drawing provenance and firmware endpoint bindings.

Settings uses switch pin2 ground and pin3 CONTROL_29; position a is active. Release uses pin3 ground, pin1 CONTROL_30/backspin and pin4 CONTROL_31/vinylbrake; position b asserts neither. Unused selector solder pads remain isolated local nets with no external wire. B3F terminals1–2 and3–4 are internally common, with a press bridging pairs; external wires attach only to1(signal) and3(ground). Pot terminal2 is the wiper,1 ground and3 analog excitation; clockwise direction remains a receiving test.

## Explicit remaining gates

This is electrical connectivity evidence, not fabrication release or power qualification. ERC uses passive contract symbols and cannot prove current rating, brightness, dynamic firmware behavior, insulation, harness retention, strain relief or thermal performance. Ring colors share eight resistor-isolated branches per sink; the segments are not independently addressable.

Common supply and ground labels express equipotential nets, not permission to insert multiple wires into one terminal. Exact mating connectors, rated distribution hardware, physical routes and plugged clearances belong to the installation package. Their adoption must be checked against these endpoint nets. Main-header unused pins are omitted at the assembly boundary; existing native main-board connectivity remains authoritative.

Pot detent allocation is unresolved. Schematics deliberately say `10k linear - detent TBD`: mechanically compatible PTV09A-6025F-B103 is the no-detent orderable candidate, while PTV09A-6225F-B103 center-detent availability requires a quote. No per-control allocation or procurement release is implied. Optical diffusion/brightness, actual switch direction, solder and wire clearances, print tolerances, and assembled physical fit remain bench/receiving gates.

## Portable source audit

`audit_sources.py` verifies every sealed input/output plus all seven upstream panel-contract sources, normalizing historic absolute provenance paths against the current repository. The exact frozen installation-r7 interface manifest and Omron B3F manufacturer PDF are retained under `reference/`; the latter matches its supplement SHA256. `relocation.py` copies only declared source files, generated outputs and transitive evidence to a temporary repository-shaped directory, regenerates the complete package, and requires all 356 generated outputs to remain byte-identical. This passes without relying on the original worktree location. Final follow-on source closure contains 51 explicit bindings.
