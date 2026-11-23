# Right ADC clamp supply

The local 5 V feed now joins A_D102 pin 2 through a 0.55 mm branch and continues to the nearby supply via. Copper overlap between that local feed and the diode land increased from 0.031 to 0.292 mm². Analog ground on the adjacent layer covers the widened copper up to the supply via clearance. [Native measurements](native-review.json)

KiCad counted 30 remaining opens, zero geometry violations, and zero schematic ERC findings. A_U201 still needs a verified ES9292QPRO land pattern. [DRC](drc.json) · [ERC](erc.json) · [Paired enclosure check](placement.json)
