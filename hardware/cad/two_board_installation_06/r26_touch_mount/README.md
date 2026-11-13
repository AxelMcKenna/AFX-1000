# Conditional C3 through-fastener revision

R26 proposes two local changes only: deepen the existing AF4.2 hex nut pockets to Z4.8 and replace the old touch head allocation with the selected screw/washer envelope. The C3 pose, post centres/OD, through holes and every other housing feature remain frozen. It is an additive cut module, not a modified shared shell. Root must apply it to the selected shell and replace only the two touch head proxies; never leave duplicate old hardware or remove all PCB heads.

Candidate parts, two of each: Accu **SSC-M2-20-A2**, **HPN-M2-A2**, **HPW-M2-A2-BL**. Exact supplier PDFs are retained under sources. Their page1 drawings were visually inspected. Nut AF3.82..4.00/height1.35..1.60; washer OD4.7..5/ID2.2..2.34/thickness0.25..0.35; screw head diameter3.62..3.8/height1.86..2.0. The screw is nominal20mm/full-thread. Unbrako's primary Engineering Guide printed pages48–49 supplies DIN912 lengthjs15 and the18..30mm±0.42 table; treating that as the conforming-length acceptance bound is an explicit standards-based inference, not an extra tolerance printed on Accu's sheet. Supplier/lot conformity still needs confirmation.

## Conditional dimensional budget

| Quantity | Range or minimum, mm |
|---|---:|
| Screw length |19.58..20.42|
| Post-seat acceptance requirement |19.9..20.1|
| PCB-thickness acceptance requirement |1.5..1.7|
| Pocket-ceiling acceptance requirement |4.7..4.9|
| Screw tip above underside |1.23..2.57|
| Lowest nut underside |3.10|
| Screw protrusion beyond nut, worst case |0.53|
| Margin after additional0.4 incomplete-tip allowance |0.13|
| Highest head top |24.15|
| Upper receiving diameter including0.2 radial registration |5.4|

Printed dimensions, PCB thickness/bore, registration and0.4 tip allowance are **unqualified project receiving requirements**. They are not guaranteed manufacturer bounds. The tip must be checked for a complete thread past the entire nut; the arithmetic does not certify thread class, torque, preload or pull-out. Current pocket ceiling1.8 fails the same budget; the original short engagement is not accepted. M2×22 plus a thin washer has insufficient underside margin under these same limits, so it is not selected. The black washer finish is not credited as insulation. The C3 mounting pads are unconnected, but copper clearance, washer bearing, creep and vibration retention need qualification.

With pocketAF4.15..4.25 and nutAF≤4, minimum nominal flat insertion clearance is0.075 per side. NutminimumAF3.82 implies corners4.411>maximum pocketAF4.25, preventing free full rotation of an undistorted regular hex. With postOD≥7.1 and≤0.1 relative centering, minimum radial material beyond pocket corners is0.996mm; this is geometry only, not strength credit. Bore≥2.35 against≤2mm shank and0.1 centering leaves0.075 radial margin. Washer registration must be controlled within0.2mm; its minimumOD4.7 over maximumboardbore3.3 then retains0.5mm radial coverage. Assembly needs a means to insert/hold the recessed nut from below; no driver or nut-retention process is selected.

The nominal model uses0.3mm washer and20mm screw, with screwtipZ1.9. It is distinct from the larger conditional upper envelope. Native positive hardware and revised posts are closed; both nominal hardware and enlarged upper envelope clear all13 component/36 tail reservations. Raw nut-seat witness is planar Z4.80000019 with numerical~6e−14mm³, retained, not called empty. Raw removed-material diagnostic contains coincident faces below the old pocket ceiling (4bad edges); its64.560276mm³ report is **not** accepted as a closed Boolean solid. Root must verify the final complete revised shell. No blanket contact waiver is exported.

## Current touch bus ownership

Frozen processor source assigns J9 to Trill Craft and J10 to AS5600. Current r62 native PCB and independent native netlist agree:

| Host | Net | C3 J1 |
|---|---|---|
|D_J1009:1|LINK_AGND|3 GND|
|D_J1009:2|LINK_V3V3_IO|4 VCC|
|D_J1009:3|LINK_SCL|6 SCL|
|D_J1009:4|LINK_SDA|5 SDA|

D_J1010 has identical nets but is not the touch port; a deliberate substitution is rejected. D_J1009 native location[230,59],90° is4mm from D_J1010[230,55]. No mating connector is chosen here: its body, wire exit and withdrawal must preserve the selected AS5600 connector/harness. C3 XRES/EVENT pins1/2 policy, module pull-ups in whole-bus budget, exact electrode/unused-channel wiring and physical tuning remain open. This does not inherit a legacy MPR121 module assumption or claim a complete touch harness.

Sources: https://www.accu.co.uk/api/product-datasheet?id=2776 ; https://www.accu.co.uk/api/product-datasheet?id=7884 ; https://www.accu.co.uk/api/product-datasheet?id=179343 ; https://unbrako.com/docs/engguide.pdf . No purchase or supplier contact occurred.
