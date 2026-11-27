# Explicit anode distribution candidate

`anode-topology.json` preserves all38 source anode endpoints and their four header25 feed assignments. It replaces an implicit equipotential with34 explicit three-conductor junctions and72 individual wire segments. Every crimp connector cavity has exactly one wire. Every junction has one incoming and two outgoing26AWG wires. No extra PCB is introduced. The balanced branch grouping is an electrical candidate; physical route optimization may change which receivers share a branch while preserving exact source nets. No routed harness or cut list is released here.

Selected candidate junction hardware: TE SOLISTRAND34130 parallel splice, for copper solid/stranded wire, aggregate509–3260CMA. Manufacturer quick-reference guide explicitly permits multiple wires when their combined area lies in range. Three Alpha5853 conductors (each7strands of34AWG) total approximately835CMA; this is above the minimum and below the maximum. Do not treat the22–16AWG label as a per-wire minimum for this parallel-splice combination. Use the manufacturer-specified tooling; QRG lists hand tool49935 for34130. Exact crimp setup, strip length, pull acceptance and post-crimp receiving inspection remain required. Do not solder-fill or fold strands to compensate for incorrect tooling.

Insulation candidate TE505872P034, VERSAFIT-3/16-0-0.9375IN, black single-wall heat-shrink, nominal23.81mm length, suppliedID≥5.21mm,recoveredID≤2.36mm,wall0.51±0.16mm. It shrinks onto the metal splice body; it does not seal or clamp the individual fine-wire ends. The harness therefore requires separate wire support and an overlap check after recovery. Keep all exposed conductor fully covered and verify the actual crimp fits the supplied tube without forcing it. Sleeve length tolerance/longitudinal change and final crimp shape must be checked before closing the receiving envelope. An initial routing allowance should not be confused with manufacturer certified final dimensions.

Sources checked2026-11-12:
- https://www.te.com/en/product-34130.html (3.58nominalOD,7.65nominal length,1.55barrelID, copper/stranded compatibility)
- https://www.te.com/content/dam/te-com/documents/appliances/global/solistrand-terminals-and-splices-qrg.pdf (multiple-wire aggregate rule and49935 tooling row)
- https://www.te.com/en/product-505872P034.html (exact sleeve)
- https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=5853 (wire)

Rejected as an automatic substitute: Raychem D-110-41 solder sleeve. Its general catalogue supports multiwire selection, but the current exact customer drawing states solid conductors. That unresolved application distinction is avoided by the explicit stranded-compatible parallel crimp. No increase to24AWG is needed for the chosen parallel-splice aggregate range. Alpha5854 research was not adopted.

Remaining: exact crimp/sleeve receiving bounds, node placement, insulated supports, complete wire curves/service allowance, electrical current/voltage-drop allocation and physical acceptance. All sources from the controls worktree are read-only and hashed. The existing sealedr10 electrical endpoint and mating reservations remain unchanged.

## Control returns and current ownership

`ground-topology.json` adds26 three-conductor ground junctions and57 wires. D_J2001 and D_J2002 each use both groundpins15/16, with seven buttonreturns perpin; D_J2003pin1 serves scene9, settingscommon and releasecommon. All29momentary switches use terminal3 forground. The two selectorcommons retainW2.1/W3.1. Potreturns remain individual wires to their dedicated3pinheaders and are not silently merged into these trees. The combined anode/controlreturn candidate has60 insulated junctions and129 wires; physical placement of all of them remains required.

`verify.py` checks every LED source pin against the native signal netlist, traces each branch to its intended feed, rejects shared contactcavities, and identifies all96sinkchannels. Four injected faults are rejected, including swapped sourcefeeds with otherwiseuniquecontacts. `verify_ground.py` independently checks all31controlreturn endpoints against the sealed switchcontract and native groundpins, and rejects swappedfeeds.

The four native D_R3001..3004 values are16.5kohm±1%. The TI typical gain/reference equation gives2.9818mA/channel; at allchannels continuouslyon the LED-anode total is286.255mA nominal. This is not a guaranteed tolerance/temperature bound. The feedallocation is:

|Feed|Unique driven channels|Typical current|
|---|---:|---:|
|D_J3002pin25|12|35.782mA|
|D_J3003pin25|33|98.400mA|
|D_J3004pin25|35|104.364mA|
|D_J3005pin25|16|47.709mA|

These are feedloads, not the24sinkoutputs physicallyassigned to eachdriver/header. A display's two commonanodepins share the same segmentload: each branch maycarry the whole affectedload, but adding bothbranchbounds would doublecount current. The verifier uses downstream uniquechannel sets, including onlythree controlled ringcurrents despite24physicalRGBdice. Resistor-only variation and nominal20°C wirevoltage drop per metre are separately labeled in `verification.json`; neither is a complete electricalrating. Contact/splice heating, actualwireDCR attemperature, digital5Vsupplycapacity and faultcurrent remain open.

Source evidence includes the exact native signalnetlist, four originalwiringCSVs, TI datasheet and cached Alpha5853 manufacturerPDF. The TE quickreference was inspected through the webreader (page10 part34130/tool49935; page11 combinedCMA rule); a new direct downloadreturned403, so no localcopy is claimed. Generation uses only the local `reference/` directory. `relocation-review.json` verifies identical electrical outputs when moved outside the repository.
