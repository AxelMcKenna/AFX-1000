# Recessed touch-nut installation tool

Additive process candidate for the unchanged r26 mount. This does not qualify mounting torque, printed strength, creep, washer centering or the completed installation. No housing, PCB, hardware, or harness geometry is changed.

A custom nonmarring hollow sleeve pushes each nut from the underside into its existing hex pocket. Nominal stem OD3.5, bore2.4, handle OD12 mm. The tool is manufactured as a separate part, not assumed available as a standard screwdriver. Proposed material is unfilled POM; tooling strength and surface finish must be checked before use. The pocket, not the sleeve, restrains nut rotation. The bore gives the screw tip somewhere to go while the sleeve holds the nut against the roof. It applies holding pressure only, not tightening torque.

The stem OD receiving limit is3.4–3.6 mm, bore2.3–2.5 mm, with lateral placement controlled to0.1 mm. Relative to the r26 minimum pocket AF4.15, radial clearance is at least0.175 mm. Relative to an accepted screw major diameter≤2.0, bore radial clearance after placement error is at least0.05 mm. These are project tooling/placement acceptance limits, not manufacturing guarantees. The nut bearing face/chamfer must leave an annulus that the sleeve actually supports; catalog nut AF alone does not prove that bearing contact. Inspect a delivered nut/tool pair before assembly.

Nominal sleeve top isZ3.2 at nominal nut bottom. The tolerance-inclusive insertion sweep reachesZ3.55, derived from maximum pocket roof4.9 minus minimum nut height1.35. Tool insertion/withdrawal stays vertical; the envelope allocates40 mm below the housing, including the handle. Hold the enclosure in a stable fixture with this underside access. Handle/hand grip access beyond the defined tool remains a process check.

Assembly sequence:

1. Install the touch board on its posts; hold it seated without bending the board. Insert the sourced washer and screw from above. Washer centering must be inspected to the existing0.2 mm limit; screw/washer clearance alone does not establish it.
2. Place one nut over the hollow sleeve with matching hex orientation. Raise the sleeve vertically into the pocket until the nut seats against its roof. Do not force misaligned threads.
3. Start the screw while holding the nut against the roof. Confirm actual engagement before relaxing the sleeve. Withdraw the sleeve vertically; the central bore clears the screw tip.
4. Repeat for the other mount. Tightening and locking require a separate qualified procedure; this tool does not establish torque or strength. Inspect underside screw-tip clearance and washer registration.

Native pinned-Linux checks: nominal tool and tolerance access meshes are closed with zero degenerate triangles/bad edges; insertion sweep versus the frozen shell with only the r26 pocket extension is EMPTY. Nominal sleeve versus complete r26 nominal hardware is EMPTY (the modeled support faces meet atZ3.2). Full current assembly and toleranced nut-bearing support still require review. `touch_nut_tool_access()` is the tool/process role for root screening; `touch_nut_tools_nominal()` is not installed hardware and must not stay in the installed assembly.
