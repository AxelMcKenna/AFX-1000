# Precision divider resistor selections

The four previously unspecified divider MPNs are now selected and applied to the isolated schematic and PCB, with unchanged values and physical footprints:

| Reference | Value | Selected MPN |
|---|---:|---|
| E_R83 | 10.7 kΩ | PLT0805Z1072LST1 |
| E_R84 | 5.76 kΩ | PLT0805Z5761LST1 |
| E_R88 | 16.2 kΩ | PLT0805Z1622LST1 |
| E_R89 | 13.3 kΩ | PLT0805Z1332LST1 |

These are explicit manufacturer ordering-table selections from [Vishay PLT document 60030](https://www.vishay.com/docs/60030/plt.pdf), revision 11-May-2026, cached and SHA-bound in `primary/plt.pdf`. `Z` selects ±5 ppm/°C, `L` ±0.01%, `S` lead-free wraparound termination and `T1` the preferred tape/reel code. Each resistance code is decoded and checked against the selected value and the 0805 range. Stock, lead time and order acceptance have not been verified; this is not a purchase action.

The source drawing was visually checked: **D is the top termination and E the bottom termination**. The bottom E interval is 0.254–0.508 mm. The 0805 body's maximum dimensions are 2.1848 × 1.397 × 0.8382 mm. Existing pads remain 1.025 × 1.4 mm at X=±0.9125 mm. The centered body/terminal dimensional screen leaves positive pad overlap and toe extension. This is a package-compatibility screen, not an assembled solder-joint tolerance guarantee.

The datasheet's ±0.01% initial tolerance and ±5 ppm/°C over −55…125°C support the existing initial-plus-temperature fractional allowance of 0.0006 at 125°C. They do not bound an arbitrary installed service life. The primary table specifies ±0.02% absolute change at 2000 h/70°C and ±0.01% one-year/25°C shelf stability. The solder-heat and 10,000 h environmental entries are explicitly **typical**, so they have not been substituted for guaranteed drift limits. Service-life qualification remains open.

Native schematic export/ERC and PCB DRC completed in the pinned Linux image. All 1104 component values and all 3476 netted pins are unchanged; selected MPNs now match the PCB. The exhaustive board comparison allows only eight MPN/datasheet field updates, preserving all copper, pad poses and 49 fills from `reference_bridge/native-01`. Exactly the two inherited ERC warnings and four unwaived DSE clearance errors remain. The circuit is not fabrication-qualified and the accepted TBP73 board is unchanged.

Run `python -m hardware.qualification.two_board_aux_current_08.precision.verify` and `python -m unittest hardware.qualification.two_board_aux_current_08.precision.test_verify`. Mutation tests reject a wrong resistance decade and a relaxed tolerance code. Self-review corrected a draft D-versus-E termination interpretation before applying the final package evidence.
