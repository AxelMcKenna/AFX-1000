# Serial audio bit clock

LINK_BCLK connects header A_J203 to the digital processor and its header D_J1005. The new branch is 117.72 mm long. A single via joins the front and In5.Cu traces, with a ground return via 2.49 mm away. Ground on In1.Cu and In6.Cu covers both traces up to their terminal clearances. [Route and ground measurements](native-review.json)

The signal via passes through the digital 5 V plane. A local adjustment to LED_46 preserves the 0.80 mm copper path to the neighboring supply via. The previous connections between supply terminals remain at all seven checked copper widths from 0.20 mm through 2.00 mm. KiCad reports 29 remaining opens, zero geometry violations, and zero schematic ERC findings. A_U201 still needs its verified ES9292QPRO land pattern. The word-select and ADC data connections remain open. Interface timing and loaded rail behavior remain unverified. [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json)
