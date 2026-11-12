# Button carrier self-review

Checked exact selected LED lands/polarity, six manufactured board outlines and thicknesses, correspondence to all retained holder holes, all 300 installed PCB pairs, actual neighboring receivers, local wires, guide pocket seating, both cap travel endpoints and the complete lighting channel map. All six native PCB designs have zero violations/opens, and all 25 functions map uniquely to the actual signal-board header nets.

Fixed concrete findings: QUANTIZE's initial wire exit hit a nudge-holder post; the top-exit design initially violated cathode-pad copper clearance; a scene bridge grazed the RGB-ring support; exact coplanar seating created a false 3D collision sheet. Geometry/routing fixes and a seating-only guard resolved these. Positive tests verify all 25 cap optical targets and all 50 mounting seats rather than accepting one arbitrary contact.

The final self-review also checked connected components, which caught a genuine loose central guide island inherited from the annular ring relief. `../connected_guide.scad` removes that unnecessary island. Its 11 native cases prove preservation elsewhere, unchanged support at all 50 seats, and one connected component in every full/split guide. Original ring/button guide meshes remain historical and must not be manufactured as the final guide. The active manifest excludes them.

Optical material/brightness/uniformity, actual PCB/print/shim tolerances, plastic-thread torque/life and complete harness mating/routing remain physical/electrical acceptance gates. The panel PCBs have no complete integrated schematic/ERC or fabrication release. The result is a concrete verified receiving design with these limitations, not a claim that the assembled product has been physically qualified.
