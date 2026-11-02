# Manufacturer information needed for the first standalone prototype

No requests have been sent and no orders have been placed. This is the
technical request content to use with the component and PCB suppliers.

## ESS ES9292QPRO

The selected codec's PCB remains incomplete. The available
[ESS datasheet](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf)
does not provide the revisioned package and recommended land-pattern inputs
required by the project's [package review](../electronics/converter/package_review/README.md).
The public [codec listing](https://www.esstech.com/products-overview/codecs/)
was checked on 2026-11-01. A focused connected-Drive search for `ES9292`
returned no matching files.

Suggested request:

> We are developing a standalone stereo audio processor using ES9292QPRO.
> Please supply the current revisioned package outline and recommended PCB
> land-pattern/assembly drawing for the exact orderable part, or an
> ESS-approved CAD footprint with its drawing revision. We need terminal
> pitch, terminal width and length tolerances, exposed-pad dimensions and
> electrical assignment, body height and standoff, and the recommended
> solder-mask, paste-aperture and thermal-via treatment. Please also confirm
> the current datasheet/errata and reference schematic, recommended ADC
> driver/loading and DAC receiver/normalisation interface, and restrictions
> during partial power or power sequencing. If these documents require an
> NDA, please advise the access process.

Do not replace the deliberately absent footprint with a generic 7 mm QFN.
The characterization ADC driver board does not complete the codec board.

## PCB fabrication and assembly

For each selected physical board, send the actual stack drawing and outputs
to the intended supplier for DFM review. Obtain explicit achievable values;
the existing proposals are not accepted supplier capabilities.

| Candidate | Process questions to resolve |
| --- | --- |
| P03 supply | Proposed copper/dielectric stack, finished thickness/tolerances and plating; identify all five SMD land/drill overlaps and specify filling/capping or redesign them; confirm mask/paste treatment and assembly inspection. |
| E28 disconnect | Proposed 1.62 mm eight-layer stack: six 80 µm copper layers and two 35 µm layers; 311 retained via drills intersect SMD copper, including 310 at paste-target lands, while native via fields say unfilled/uncapped. Reconcile the historical filled/capped requirement with a location-specific process and stencil map; include the single retained 0.2 mm drill, annular ring, registration, mask, plating and thermal limits. See the [current drill/land map](staging/e28-branch-cleanup-native-12/drill-land-locations.csv) and [captured stack](staging/e28-cleanup-review-01/construction-review.json). |
| NF negative protection | Proposed 1.2 mm six-layer stack, tolerance range, copper and plated-hole process; 0.65/0.3 mm logic vias; two-sided assembly and through-hole lead projection. |
| Fan protection | Proposed 1.2 mm four-layer stack and tolerance range; connector receiving thickness, assembly and lead projection. |
| AC04 partial audio main | U201 package/land and interface data remain missing; do not produce order files from the partial routing. Nominal four-layer 1.6 mm construction, stack and tolerances need acceptance. Local surface routing width is 0.20 mm and supply trunks use 0.60 mm on inner and outer layers; only intra-footprint pad pairs in the four retained U101/U102/U105/U106 VSSOP instances use the inherited 0.15 mm requirement. Confirm copper, mask/paste, registration and two-sided assembly; component-height limits, complete connector mates/wire paths, shared M2 support stack and final mounting remain unapproved. The current 356 conventional 0.60/0.30 mm vias have a minimum screened drill-edge-to-SMD-copper gap of 0.16998 mm; none intersects a solder land. Mask registration/tenting, stencil and stack processing still need acceptance. Classify the four bare test pads as non-fitted copper features in the assembly BOM. The In1 reference plane connects all 200 placed AGND pads, with sensitive-node openings reserved on both inner layers; all 161 placed rail/sense pads connect to their sources, but codec lands, complete installed distribution/return and thermal/noise/stability qualification are unfinished. See the [partial routing and reference-plane holds](staging/audio-main-controls-02/README.md). |
| DC04 digital core | Four-layer construction and actual copper/dielectric stack remain to be specified and accepted. The 243 vias include 107 new 0.60 or 0.65/0.30 mm signal vias; their minimum screened hole-edge-to-SMD-copper gap is 0.16998 mm. The 136 DC03 vias remain exact: 115 clear SMD copper by at least 0.15 mm and 21 occupy mask-covered LED heat-spreader copper at least 0.98 mm from package solder openings. Those 21 request front/back tenting; filled/capped processing is not assumed. Review the [new-drill map and preserved evidence](staging/digital-four-clean-native-03/handoff.json), annular ring, mask registration/tenting, stencil, two-sided assembly, sockets and THT solder/tail receiving. There are 143 opens. SD carrier lengths/via counts need correction and the complete interface needs a timing/reference/impedance budget. The separate six-layer 113-open trial is unselected and has no accepted physical stack. Power/return/thermal and installed-fit qualification remain unfinished. |

For all boards, resolve exact orderable BOM entries, alternatives requiring
approval, finish, assembly side, polarity/orientation, panelisation and
test/inspection access. Confirm final mating connectors and mounting
hardware against the accepted mechanical assembly.

The E28 map uses actual front/back SMD copper and a conservative polygon screen.
It includes passive, IC and SMT power-terminal lands; their appropriate solder,
thermal and connector treatments require individual review. Its 0.1 mm proximity
threshold is a screening aid, not an accepted factory clearance. Historical E28
generation and terminal-stitching notes specify a candidate filled/capped process,
but the current native fields and manufacturing instructions are not reconciled.
Zero native DRC/ERC findings do not resolve that discrepancy.

Prototype manufacturing does not require measurements of boards that have
not yet been built. It does require a complete reviewed design and a defined
first-article inspection and safe bring-up plan. Production release requires
the subsequent measured qualification.
