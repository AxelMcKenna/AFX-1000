# KiCad report-limit correction

Stock KiCad10.0.7 limits each unconnected/clearance report to499 markers and
other categories to199. `--all-track-errors` does not remove those limits.
The official [DRC engine source](https://gitlab.com/kicad/code/kicad/-/raw/10.0.7/pcbnew/drc/drc_engine.cpp)
defines the constants at lines58–59 and applies them in `RunTests`.

A499-entry result is therefore a capped report, not a complete connection
count. [measurements.json](measurements.json) binds independent uncapped native
connectivity counts to the exact PCB bytes. The reader rebuilds connectivity,
recalculates the ratsnest and calls `GetUnconnectedCount(False)` to include
hidden nets. It does not change or reroute any board.

The NF06P265-part starting placement has750 actual missing connections, while
its original report lists499. Its first signal trial has433. A separate local
power/bypass stage has487, down263 from the actual750 starting point. Both
partial stages retain zero other strict native findings. Neither is complete
or fabrication-ready. Earlier sealed reports remain unchanged; old499 labels
must not be treated as uncapped totals.

Zero-finding FPC electrical checks remain zero; a positive report limit does
not invalidate a zero result. Those boards still need the separate physical,
source-current, fault, PDN, noise, temperature and whole-unit qualification.
