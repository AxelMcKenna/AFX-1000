# Panel endpoint checkpoint

`panel-contract.json` binds all32 active-low front inputs,30 pot terminals and5 selector leads to the current signal-board native netlist and actual pad inventory. It includes source hashes. `button-contact-contract.json` supplements its deliberately frozen pending button-contact field with the manufacturer-verified B3F-1000 contact pairs. These are electrical contracts, not a completed cable assembly or fabrication release.

The C&K selector circuit diagrams were inspected on page4 of the controls team's saved manufacturer JS series document (22Sep2022). Settings uses common2 and throw3: positiona active, positionb inactive. Release uses common3 and throws1/4: positionc backspin, positionb neither input, positiona vinylbrake. Unused throws and the entire second poles remain local isolated nets, with no external wire. Do not ground release terminal2: that would make the center position electrically active.

Bourns PTV09 manufacturer page1 identifies wiper2 and element ends1/3; page3 gives PTV09A-6 terminal numbering. Connect1 toAGND,2 to the indexed POT_RAW net and3 toV3V3_ANALOG. Confirm increasing clockwise voltage on receipt because the schematic does not explicitly label rotation at the element ends. No-detent PTV09A-6025F-B103 and center-detent procurement candidate PTV09A-6225F-B103 remain distinguished by the controls team's receiving documents.

Omron B3F manufacturer page4 identifies always-connected pairs1–2 and3–4; buttonpress joins both. Use1 forCONTROL_nn and3 forAGND. The bottom-view logo reference is retained in the supplement. These switch leads are separate from the25 button indicator PCBs.

Both selectors and scene9 share D_J2003 groundpin1. This requires a specified rated distribution/splice. Likewise the29 buttons cannot be silently terminated several wires per contact. Distribution hardware, exact main connector pairs, cable poses/lengths and strain relief are still under development. Existing generic boxes are not an approval of any newly selected housing height.

Run `PYTHONDONTWRITEBYTECODE=1 python3 hardware/cad/two_board_installation_06/r10_interfaces/panel_contract.py` from this isolated worktree. The generator reads the controls team's isolated source files, requires them to exist and records their hashes; changing those files changes the generated output. The checked-in JSON is the sealed checkpoint consumed by panel schematic integration.
