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
| E28 disconnect | Proposed eight-layer mixed-copper stack and thickness; the retained 0.2 mm finished drill and its land/capping requirements; annular ring, registration, mask and thermal limits. |
| NF negative protection | Proposed 1.2 mm six-layer stack, tolerance range, copper and plated-hole process; 0.65/0.3 mm logic vias; two-sided assembly and through-hole lead projection. |
| Fan protection | Proposed 1.2 mm four-layer stack and tolerance range; connector receiving thickness, assembly and lead projection. |

For all boards, resolve exact orderable BOM entries, alternatives requiring
approval, finish, assembly side, polarity/orientation, panelisation and
test/inspection access. Confirm final mating connectors and mounting
hardware against the accepted mechanical assembly.

Prototype manufacturing does not require measurements of boards that have
not yet been built. It does require a complete reviewed design and a defined
first-article inspection and safe bring-up plan. Production release requires
the subsequent measured qualification.
