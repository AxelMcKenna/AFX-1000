This private J29 repair starts from frozen spaced fanout `e4156603…`. Combined integration found the original header's mated/service envelope intersecting return retention. This source moves only **J29**, retaining its part, footprint, three nets and service envelope. All other87 complete footprints, all79 schematic parts/pinmaps, new output ports, H9, board outline, layer stack and quiet-filter values/poses remain exact. Canonical and all parent seals stay unchanged.

Actual native KiCad transforms verify the proposed−90° pose at native(240.4,157.8):

| Pin | Net | Native centre (mm) | World centre (mm) |
|---|---|---|---|
|1|AGND|(240.4,157.8)|(170.4,99.8)|
|2|POT_RAW_09|(237.86,157.8)|(167.86,99.8)|
|3|V3V3_ANALOG|(235.32,157.8)|(165.32,99.8)|

Native saved−90°/270° equivalent angles are checked modulo360 without double-adding the footprint rotation. Native front courtyard plus the inherited0.5 mm each-side service allowance gives world[163.055,97.535..172.665,102.065]. This is approximately0.8 mm right of the initial analytic suggestion; the actual serialized geometry is authoritative. No native front courtyard intersects another part. ADC's separate captured-packet assessment found0.535 mm nominal gaps to E18's front edge and H4 head and3.935 mm to the retainer. Those scalar/box findings are not renewed native or physical integration acceptance; actual header bodies, tails, support/head and return hardware still require the new independent MCAD run.

Only four source segment objects are replaced, with no new vias:

- POT_RAW_09's final two0.25 mm In2 segments reconnect new pin2 through(237.86,160.25) to the unchanged(230.25,160.25) anchor. Every downstream route to R40.1 and the original filter circuit remains intact.
- The0.4 mm F.Cu analog-reference stub moves to new pin3 and the existingY163.7 trunk. That trunk's last1.18 mm is trimmed so its endpoint is connected rather than dangling. All other pot feeds remain exact.
- New AGND pin1 connects through actual native In1 fill after refill. No artificial ground link or ideal pad/via short is added.

`generated/design-change.json` records exact removed/added objects and old/new J29 footprints. The reviewer verifies the footprint changed only its actual placement/pad angles, removes the four declared replacements and recreates the complete original unaffected source in its original object order. The schematic, BOM, components and libraries are unchanged; all79 native pinmaps are compared.

Fresh native ERC/all-severity DRC/parity/connectivity must be zero before the final seal. Separate actual copper polygons recheck the entire3.8 mm H9 disk on all four layers and actual source/output flood connectivity, without inheriting old proof. `generated/native-orientation.json` binds the real new J29 pad/courtyard/service coordinates. Three tests reject six undeclared-object mutations and check current source, native and copper evidence.

The source still has J13 input, J14 bypass/gain output and J15 monitor output. The positive2.4 A capacity allocation retains1.984 A assigned branches and0.416 A unassigned reserve, with no invented endpoint. The old global manifest is not silently changed. Destination boards/harnesses/joints and complete signed return currents remain unqualified.

The frozen e415/f2db coarse PDN does **not** transfer to this layout: the three header holes, local analog-reference/raw routes and actual copper have changed. A new source-bound extraction is required after the physical pose is accepted. No full tensor solve is run here. Full mechanical integration, electrical headroom, noise/current/thermal/process, physical and fabrication-release flags remain false pending actual evidence.
