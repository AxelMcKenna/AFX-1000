# Panel ground drawing matched to the selected formed harness

Open `assembly/panel.kicad_pro` for the 39-page panel drawing. This amendment
supersedes the r12 ground schedule and matches the selected r14/r15 formed
routing: D_J2002 pin 15 feeds the 19 non-scene buttons; pin 16 feeds the ten
scene buttons and the two selector commons through one splice. D_J2001 pins
15/16 and D_J2003 pin 1 have no external ground wire in this topology.

All 29 button notes name their exact incoming and outgoing terminals and neighbor
contacts. Incoming ground alternates between terminal 3 and terminal 4 according
to the physical route. Terminal 1 remains signal and terminal 2 is externally
unwired. There are 28 outgoing button contacts; Hold terminal 4 is the sole
unwired ground-chain end. `terminal-schedule.csv` maps control names to schematic
references. `wire-schedule.csv` records all 32 external ground wires, including
the three splice connections and selector commons. These are adjacency schedules,
not qualified cut lengths or instructions to omit the other signal wires.

Strict native Linux KiCad ERC passes with zero errors, zero warnings and no
ignored checks. All 349 components, their values/footprints/datasheets and every
pin net remain identical to the preserved panel electrical baseline. Only text
on the switch sheet changes; other assembly files are byte-identical. The host
verifier independently checks both CSVs against the source contract and rejects
wrong outgoing contacts and wrong terminal directions. Source hashes bind the
current ground contract and its dependencies.

The native SVG was rendered in three overlapping detail views and visually
reviewed across all 29 notes. Labels fit below their symbols; the legend clears
the page border. Original native SVG and images remain in `drawing/` for zooming.
The underlying panel hierarchy is unchanged.

Ground supports, strain relief, service slack, actual terminals, the remaining
panel harness and physical tests are still incomplete. This is not fabrication
release. Previous r12 artifacts are retained as historical evidence and must not
be used as the current adjacency schedule.

Reproduce into a fresh output location using `build`, pinned Linux KiCad
`verify --strict-native`, then host `verify` from this module package. The
verifier deliberately refuses to overwrite an existing verification record.
