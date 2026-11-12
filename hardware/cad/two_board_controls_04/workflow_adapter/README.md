# Controls workflow adapter

`registry.json` is the merge input for the unified assembly. Import `controls.scad` with OpenSCAD `use` and call the registered zero-argument modules. Coordinates are housing world millimetres. Render only `role: installed` by default; motion and receiving rows are independently selectable checks.

The adapter delegates to frozen sources without changing their geometry. It distinguishes physical lenses and panel hardware from maximum shafts, generic pot body allocations and wiring allowances. Installed purchased-part references are simplified geometry, not certified supplier solids. All 29 keycaps preserve the frozen shape; switch references omit terminals. Springs and compliant pucks remain omitted because the frozen mechanism combines those with separately owned holders. No generic captured control boxes are added.

The registry binds 34 passive control board instances across 12 designs, in addition to the two main boards and separately owned sensor board. Its selected electrical project is `panel_electrical/assembly/panel.kicad_pro`; its complete assembly subtree is hash-bound, including 39 schematic pages. This does not release fabrication or prove current capacity or complete housing fit.

Run `python3 hardware/cad/two_board_controls_04/workflow_adapter/verify.py` from any directory. It checks recursive SCAD and schematic source closure, exact delegate tokens, installed/receiving separation, PCB quantities and hashes. Four deliberately corrupted registries must be rejected. `build_registry.py` regenerates the adapter and manifest only after the frozen source selection has been reviewed; changing a hash does not qualify a design change.

Self-review found that a top-level electrical glob omitted child sheets; fixed by binding the complete selected assembly subtree and checking recursive Sheetfile closure. Static verification passes with 26 components, 308 source files, 34 PCB instances and 12 designs. Native export is delegated to the root integrated runner: the initial repository-qualified image lookup was unavailable locally and its attempted fetch timed out. Root confirms the same pinned image ID exists and will use its established `--pull=never` runner. No native CAD result is claimed here.

Intentional contacts describe seating only and are not blanket interference exemptions. The final connected guide and lid remain separate components from the button indicators. Parent assembly checks must assess these contacts and other installed combinations.
