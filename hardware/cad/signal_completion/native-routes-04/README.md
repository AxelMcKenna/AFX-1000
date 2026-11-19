# Codec run-control connection

Six 0.20 mm In3.Cu segments join the existing audio and digital groups of LINK_CODEC_RUN. This completes one control connection between sections and takes the board from 142 to 141 open connections. The 29.30 mm route uses the existing plated transitions and preserves all saved zone fills.

KiCad 10.0.7 passes geometry and schematic ERC checks. Schematic parity still reports the missing ES9292QPRO footprint at A_U201. The native copper review covers the connected adjacent reference fields and the existing same-net transition clearances. The codec's startup behavior and timing still require electrical validation.

[Native routing and reference checks](../routes-04-review.json) · [Project DRC](drc.json)
