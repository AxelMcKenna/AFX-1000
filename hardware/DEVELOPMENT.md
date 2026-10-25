# Higher-headroom standalone development handoff

This work applies to the 12 V input, higher-headroom external-converter design. B1 is the separate 5 V budget design. The B1 adapter and earlier A08–A11 CAD sources remain separate. The maintained sample reader now has an explicit F06 kernel-transport opt-in; its default table and desktop behavior remain covered by regression tests. Native checks and host builds do not qualify a complete physical unit.

The second review adds [P02 source and full-distribution analysis](electronics/power_distribution/p02/README.md), an [E26 escape-first layout](electronics/rail_disconnect/revision26/README.md), an [E12 ADC characterization board](electronics/adc_driver/pcb/README.md), the [ESS package/register audit](electronics/converter/package_review/README.md), and [F06 maintained-engine firmware](firmware/full_engine/README.md). These are explicit new variants, not interchangeable files for the earlier assembly. P02 requires a higher-rated input guard, new quiet-star returns, return bars and thermal paths. Their implementation and enclosure fit remain open. E12's sense stars end at its J2 header; the final converter requires co-location or a revised force/sense interface.

E26 is frozen as a partial pilot: 7,935 segments and 496 vias, 21 open connections, 30 native warnings and zero schematic-parity issues. The warnings are 29 dangling escape stubs and one copper sliver. Its strict check fails as expected; byte-exact replay is a recovery tool, not a routing or fabrication pass.

F06 brings the current 152-parameter DSP and 122 advanced User settings into SRAM-boot firmware. Exact kernel packing removes the original SRAM overflow without coefficient quantization. Its boot sample limits and physical qualification gaps remain explicit. The F05 build below remains available as the earlier snapshot.

The standalone CI workflow now includes F06 payload-freshness and host tests. This local batch has not been committed or pushed, so those new workflow steps have no remote CI result yet; local build/test receipts are separate evidence.

The [board inventory](wiring/board_readiness/generated/board-readiness.json) now recognizes E12 as a separate routed candidate. Four baseline boards still lack PCBs: rail monitor, converter, DAC receiver and sequenced bypass. Converter U1 lacks a dimensioned manufacturer land-pattern drawing; its footprint remains unassigned. The selected sensor/SD, LED-anode and distribution assemblies are also unfinished.

The table below preserves the first parallel-pass handoff. Its archived evidence remains immutable; second-pass records carry their own source hashes and scope. The existing Q01 bench plan describes the older E14/E25/F05 assembly and must be revised before testing a P02/E26/F06 unit.

| Workstream | Reviewable result | Remaining boundary |
| --- | --- | --- |
| 5 V source/distribution | [P01 candidate and corner analysis](electronics/power_distribution/README.md) | Conditional DC budget ends at the E25 protected output star. New PSU schematic/layout, outgoing fanouts, capacitor stability, inrush and actual resistance/thermal qualification remain open. |
| E25 disconnect routing | [Independent copper candidate](electronics/rail_disconnect/routing/README.md): 2,538 tracks, 178 vias, zero native DRC/parity issues, 123 opens | Escape congestion and power/ground losses require further routing and possibly a new placement revision. Existing placement and A11 evidence are unchanged. |
| Other boards and wiring | [320 logical interconnects](wiring/SYSTEM.md), [board readiness inventory](wiring/board_readiness/generated/board-readiness.json) and a separate [E10 input-board candidate](electronics/input_range/pcb/README.md) | Sensor/SD assemblies, LED anodes, production contacts/fanouts, remaining analog/converter boards and physical integration remain unfinished. A logical contact name is not a verified purchased-part pin number. |
| Standalone storage | [F05 read-only boot loader](firmware/STORAGE.md), 27 host CTest groups and both ARM profiles | Two-second bounded sample files and project boot/User formats; no original RSD compatibility, hot reload, writing or measured SD/current/DMA/audio behavior. |
| Mechanical trials | [Compact A11 fit kit](cad/a11_fitkit/README.md): 30 STL designs / 38 copies and 16 native checks | All 46 measurement rows are pending. Printing, purchased-part dimensions, fit, feel, retention, force and durability require real parts and measurements. |
| Powered qualification | [Q01 bench plan](qualification/README.md): 39 staged cases and source-bound capture validation | Zero physical measurements performed. Missing evidence, incomplete designs and unqualified limits cannot become passing results. No full-unit power-up release is granted. |

The E10 PCB candidate is not placed in the A11 enclosure and has no physical audio, thermal, EMI or complete footprint/manufacturing qualification. The system wiring packet retains its declared baseline board sources; the new E10 candidate has its own interface and native-copper evidence.

The compact fit-kit ZIP is generated under `build/artifacts/cad/a11-fitkit/`. The matching source, purchased-part table, pending measurement sheet and validation receipt are included in this work. Its largest part is 38 × 32 × 18 mm; no full chassis needs to be printed to begin those mechanical trials.

The main unresolved electrical architecture is the complete 5 V path, including outgoing load wiring and real power/ground copper. The P01 source candidate does not resolve E25's incomplete routing or substantiate the old copper-resistance allocation. Preserve the original voltage targets when revising the source, interlock, connectors and board placement; do not relax them to make a trial pass.

Current software tests and conditional analyses are recorded separately from physical evidence. Historical records retain their original snapshot scope and hashes. The newest parallel-work verification record accompanies this handoff; existing review archives remain immutable. No board ordering, flashing, physical printing or powered testing was performed by these workstreams.
