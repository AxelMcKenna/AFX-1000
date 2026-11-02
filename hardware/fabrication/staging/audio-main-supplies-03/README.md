# AC04 — intermediate outer-layer supply connections

This retained Linux KiCad 10.0.7 checkpoint adds 28 surface joins / 248 tracks
to the earlier inner distribution. It has **278 opens**, **150/161** placed
supply/sense pads connected to source, zero geometry/ERC findings, one missing
codec footprint warning, and no ignored categories. The four ±12/±19 V rails
are connected at every placed terminal. All original local/control and 200
ground connections remain intact. No vias or plane-fill changes are added.

Its handoff records the intermediate native checkpoint. The combined actual
copper, per-terminal and native-fill audit is now provided by the selected
[placed-rail completion candidate](../audio-main-supplies-06/README.md).
Neither checkpoint is ready for fabrication; codec land, remaining signals,
installed electrical/thermal performance, parts/process and assembly receiving
remain unfinished. No board order was produced.
