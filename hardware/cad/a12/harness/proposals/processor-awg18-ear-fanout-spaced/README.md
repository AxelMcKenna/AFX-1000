This private spacing repair follows the frozen electrically closed, service-rejected `processor-awg18-ear-fanout` source `b743a449…`. Root's actual native mutual-service collision was15.0982246 mm³; its snapshot/SCAD/STL remain in that immutable parent. This candidate **moves only J14's physical row fromY87.5 toY84.5** and extends the ear topY85→Y82. EastX194.5, J15, J13 and H9 remain fixed. The In1AGND ear contract explicitly extends to nativeY140; the positive contracts already cover this material. No clearance, pad, joint or service envelope shrinks.

The output rows now have8 mm pitch. With the inherited actual front-courtyard plus0.5 mm each-side service boxes, that leaves **3.1 mm nominal service gap**, compared with the failed0.1 mm. Additional board material is43.5 mm². New nominal copper land clearance stays0.8 mm at top/right versus the unchanged0.5 mm rule. Root/ADC own fresh actual material, body, case, solder/service, wire and tool MCAD; no new mechanical pass is inferred from this scalar gap.

| Interface | Positive / AGND world pad centres (mm) | Retained positive allocation |
|---|---|---:|
|J13 input|(188,100) / (188,104)|2.4 A maximum allocation|
|J14 bypass/gain output|(188,84.5) / (192,84.5)|0.140 A|
|J15 monitor output|(188,92.5) / (192,92.5)|0.080 A|

H9 remains(182,92.2). Native KiCad transforms verify the actual horizontal4 mm output pitch at90° footprint orientation; saved angles are not double-added. All other87 complete footprints, all79 schematic parts/pinmaps, original routing/quiet filters, stackup and H9 exclusion remain exact. The schematic, BOM, component inventory and libraries are byte-identical to the parent. Only J14's board placement and four declared edge/zone contracts change.

Fresh native ERC/all-severity DRC/parity/connectivity must be zero before the seal. Separate native polygons check the complete3.8 mm H9 metal disk against all four layers' actual copper, without soldermask credit. Filled-copper/pad probes test source-to-both-output connectivity on F/In2/B+5V and In1AGND, alongside local source/west continuity and independent upper/inter-hole cut controls. These geometric checks do not establish resistance, ampacity or noise. No full tensor solve or prior PDN inheritance is used.

The proposed source tree remains E28J4→E19J13, then J14→sequenced_bypass J1.1/J1.2 and J15→rail_monitor J1.1/J1.3. The retained shared2.4 A ledger is Seed1 A +LED0.764 A +bypass/gain0.140 A +monitor0.080 A +**unassigned reserve0.416 A**. This proposal replaces the original manifest's E28-star branches if adopted; never duplicate both allocations. J1 remains unfitted service access. Shared3V3/control/bipolar return currents and pin sharing require a signed coupled model, not equality to positive branch current.

Single-AWG18 maximum1.4 mm pretinned bundles,2.1..2.3 mm finished bores and3.4 mm lands remain requirements, with no multiwire or solder/strain/lifetime approval. Destination native PCBs, mating assemblies, physical wire routes and source-to-load voltage/current qualification remain missing. Every new part's value/footprint is checked against native schematic, BOM and component inventory. No reserve endpoint is invented.

`generated/package-review.json` restores the declared source edits to recreate the full old board and checks every old pinmap. `generated/native.json` contains actual raw CLI/ERC/DRC/fill/netlist evidence with current hashes; `generated/current-native.json` indexes the sealed package. Three tests reject five undeclared object edits and check actual source/port/flood evidence. All physical, whole-service/wire, mechanical integration, PDN and fabrication-release flags remain false here pending independent evidence. Canonical and all older seals remain untouched.
