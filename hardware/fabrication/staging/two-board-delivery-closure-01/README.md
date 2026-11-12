# Power-board delivery dependency audit

The recursive audit starts at TBP71 and follows explicit source hashes, hardware file references and static absolute Python imports. It identifies 49,849 source/evidence files, including 7,165 initially untracked files. All newly staged dependencies are under hardware/fabrication; unrelated workspace files are excluded.

There are no missing bound files. The 26 recorded historical hash mismatches refer only to the two public overview READMEs, which changed as the design advanced. This does not establish replayability of historical documentation checks. Current TBP71 final-review source bindings were separately verified unchanged. Dynamic imports, external tools and execution from a clean checkout still need verification before reproducibility is claimed.

The ignored KiCad per-user `.kicad_prl` preference file is excluded from delivery. It is not a circuit or board source. Generated KiCad SVGs retain their native whitespace so recorded artifact hashes remain valid: `git diff --check` reports 164,728 SVG trailing-whitespace lines, with no other file type reported. Do not rewrite those source-bound outputs for formatting.

This is a dependency-preservation checkpoint, not a fabrication release. TBP71 retains 1,943 open connections. The attempted evidence generator rerun reached its existing-output guard after all source, native connectivity and reference assertions passed; it deliberately refused to overwrite `final-review.json`. The separate read-only hash check verified the existing final record's 277 source bindings.
