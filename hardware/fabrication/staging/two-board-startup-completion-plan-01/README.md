# Remaining startup logic construction plan

Development candidate from TBP42; not a fabrication release. U30, U34 and U41
move together with their existing 100 nF capacitors C75, C77 and C84. All pin
escapes were reserved before interconnect routing. U41 sits between analog and
digital circuits. Parts, packages, values and pin nets remain unchanged.

The candidate restores all connections affected by the moves and adds master,
receiver, follower, AUX supply, local bypass and main-return joins. Existing
In1/In4/In5/In6 main-ground reference outlines extend around the routes. Quiet
returns and retained bottom-trace reference areas are excluded from In6 routing.

Three interconnects remain deferred: analog enable to U13, its R96 signal end,
and the ANA_PG1 pull-up R99 signal end. Unused U30.3, U13.1, R99.1 and R96.1
fanout tracks/vias are not emitted. The native partition audit must prove the
expected 24 joins and preservation of every other connection.

The initial 0.1 mm searches failed or exhausted their bounded windows. The
selected coarse-to-fine free-space search uses a wider window and still checks
every resulting path against the original copper/mount screen. The scratch
search scripts retain temporary paths; plan.json is the construction input.
Native DRC/ERC/parity, ground ownership, reference coverage and visual review
remain required. Geometry does not establish timing, noise or current limits.
