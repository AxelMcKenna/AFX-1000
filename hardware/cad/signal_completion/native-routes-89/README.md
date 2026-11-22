# Gain-request interconnect

LINK_GAIN_REQ connects Daisy socket D_U1001 pin 10 to A_J602 pin 4. The 0.20 mm route measures 240.14 mm across In2 and In3. Both layer changes have a ground via within 0.82 mm of the signal via. Native refill confirms the adjacent ground copper connects to each return via and preserves the reference copper beneath previous traces and lands.

KiCad verified 37 open connections, zero geometry violations and zero ERC findings. The signal board still requires the ES9292QPRO footprint for A_U201.

The route narrows part of the digital 5 V pour. At four simultaneous 96 mA LED-header loads, the largest modeled board drop across four mesh pitches increased from 6.09 to 6.60 mV. The largest increase at the same header and mesh was 0.80 mV. The calculation assumes 18 µm copper at 20 °C and 20 µm via plating. It covers the header anode paths. The complete rail, cable, and LED voltage margin still require qualification.

[Routing and ground checks](reference-review.json) · [Sheet model](power-sheet.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
