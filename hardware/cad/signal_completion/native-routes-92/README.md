# LED channel 14

D_U3001 pin 19 connects to D_J3002 pin 10 through 36.17 mm of 0.20 mm copper. One 0.65 mm via with a 0.30 mm drill carries the channel from front copper to In2. Both legs share one continuous In1 ground region. Short sections of LINK_ARMED, CONTROL_09 and LED_16 move around the new drill. The native check confirms ground coverage along each replacement and the earlier control-route transitions.

With four simultaneous 96 mA header loads, the largest modeled drop across four mesh pitches changed from 6.295 to 6.294 mV. The copper and barrel model assumes 20 °C. Loaded rail margin and cable drop still require measurement.

KiCad verified 34 remaining opens, zero geometry violations and zero ERC findings. The signal schematic still calls for the ES9292QPRO footprint at A_U201.

[Routing and ground checks](reference-review.json) · [Control return checks](control-stitches.json) · [Revised armed route](armed-route.json) · [Supply model](power-sheet.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
