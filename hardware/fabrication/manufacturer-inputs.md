# Manufacturer information needed for the first standalone prototype

No requests have been sent and no orders have been placed. This is the
technical request content to use with the component and PCB suppliers.

## ESS ES9292QPRO

The selected codec's PCB remains incomplete. The available
[ESS datasheet](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf)
does not provide the revisioned package and recommended land-pattern inputs
required by the project's [package review](../electronics/converter/package_review/README.md).
The public [codec listing](https://www.esstech.com/products-overview/codecs/)
was checked again on 2026-11-04 and still links the 183-page v0.1 datasheet.
A focused connected-Drive search for `ES9292` on that date returned no matching files.
The focused official-site search did not locate the missing revisioned package/land/stencil drawings.

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

The current consolidation target is two main PCBs. The [integrated signal
checkpoint](staging/two-board-signal-routed-native-03/README.md) has a provisional
eight-layer, nominal 1.6 mm construction, 917 retained vias and 251 opens.
Its 268 × 63 mm outline and the 320 × 181.1 mm C-shaped power-board proposal need
supplier review for stack, copper balance, bow/twist, support during assembly,
panel handling, mask/paste, via treatment and two-sided assembly. The power PCB
has an integrated schematic and partial native routing; the [current fabrication
inventory](README.md) identifies the selected project, checks and remaining
connections. The separate-board stack/process entries
below are historical engineering inputs; they do not transfer automatically to
the consolidated boards. No manufacturing stack or supplier is selected for
the two-board candidate, and neither is an order source.

For each selected physical board, send the actual stack drawing and outputs
to the intended supplier for DFM review. Obtain explicit achievable values;
the existing proposals are not accepted supplier capabilities.

| Candidate | Process questions to resolve |
| --- | --- |
| P03 supply | Proposed copper/dielectric stack, finished thickness/tolerances and plating; identify all five SMD land/drill overlaps and specify filling/capping or redesign them; confirm mask/paste treatment and assembly inspection. |
| E28 disconnect | Proposed 1.62 mm eight-layer stack: six 80 µm copper layers and two 35 µm layers; 311 retained via drills intersect SMD copper, including 310 at paste-target lands, while native via fields say unfilled/uncapped. Reconcile the historical filled/capped requirement with a location-specific process and stencil map; include the single retained 0.2 mm drill, annular ring, registration, mask, plating and thermal limits. See the [current drill/land map](staging/e28-branch-cleanup-native-12/drill-land-locations.csv) and [captured stack](staging/e28-cleanup-review-01/construction-review.json). |
| NF negative protection | Proposed 1.2 mm six-layer stack, tolerance range, copper and plated-hole process; 0.65/0.3 mm logic vias; two-sided assembly and through-hole lead projection. |
| Fan protection | Proposed 1.2 mm four-layer stack and tolerance range; connector receiving thickness, assembly and lead projection. |
| AC04 partial audio main | U201 package/land and interface data remain missing; do not produce order files from the partial routing. Nominal four-layer 1.6 mm construction, stack and tolerances need acceptance. Local surface routing width is 0.20 mm and supply trunks use 0.60 mm on inner and outer layers; only intra-footprint pad pairs in the four retained U101/U102/U105/U106 VSSOP instances use the inherited 0.15 mm requirement. The dedicated U208.1 SENSE branch uses 0.20 mm copper over 10.073 mm under a separate 12 mm low-current construction limit; the VDD and pull-up feeds retain short entries. Confirm copper, mask/paste, registration and two-sided assembly; component-height limits, complete connector mates/wire paths, shared M2 support stack and final mounting remain unapproved. The current 382 conventional 0.60/0.30 mm vias have a minimum screened drill-edge-to-SMD-copper gap of 0.16998 mm; none intersects a solder land. Mask registration/tenting, stencil and stack processing still need acceptance. Classify the four bare test pads as non-fitted copper features in the assembly BOM. The In1 reference plane connects all 200 placed AGND pads, with sensitive-node openings reserved on both inner layers; all 161 placed rail/sense pads connect to their sources, but codec lands, complete installed distribution/return and thermal/noise/stability qualification are unfinished. See the [partial routing and reference-plane holds](staging/audio-main-controls-06/README.md). |
| DC04 digital core | The selected [four-layer DC04](staging/digital-four-clean-native-03/README.md) still has 143 opens and is not an order source. Its 243 vias include 107 new signal vias with a minimum screened drill-edge-to-SMD gap of 0.16998 mm, plus the 136 retained DC03 vias. The latest separate [eight-layer comparison](staging/digital-led16-closed-native-01/README.md) has 27 opens (SERIAL_0 and 26 LED outputs), 3,342 tracks and 535 vias, with zero other native layout/parity/ERC findings and every check category enabled. Its four actual plane copper unions remain connected, all 201 power/ground pads and 32 front-control inputs remain connected, and SD carrier planar length spread is 5.999239 mm. The minimum non-exempt drill-edge-to-SMD gap is 0.154984 mm. Twenty-one retained mask-covered LED heat-spreader vias require explicit front/back tenting and mask-registration review; filled/capped processing is not assumed. New signal vias use 0.60/0.30 mm geometry, and native track-width/clearance requirements remain 0.20/0.20 mm. The twelve newest tracks have a measured nearby foreign-copper gap of at least 0.203657 mm; this does not establish supplier capability. Obtain an actual eight-layer copper/dielectric stack, finished thickness/tolerances, plating and annular-ring acceptance, mask/paste treatment, two-sided assembly, socket/THT solder-tail receiving, cost and impedance requirements. The nominal 1.6 mm setting is not an accepted stack. CONTROL13 is now 40.498 mm/one via, LED16 is 53.962 mm/one via; LED09 and LED10 remain 124.070 mm/one via and 173.462 mm/four vias. Long LED, control, latch, CODEC_RUN, pot and bus routes retain their documented timing, loading, settling, PWM coupling, return-path, thermal and EMC qualification holds. The linked checkpoint preserves the earlier routing tradeoffs and physical evidence. This comparison is unselected and incomplete; do not generate order files from it. |

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
