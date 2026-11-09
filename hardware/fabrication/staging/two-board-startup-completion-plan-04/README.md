# Startup routing and reference cleanup candidate

Development candidate from TBP42, not a fabrication release. Retains the six
U30/U34/U41 and local bypass moves. Routes the analog enable and both analog
PG pull-up signal ends. FOLLOW3 to the digital eFuse remains deferred; its
unused U34.7 fanout is omitted. Expected net new connectivity is 26 joins.

Routes avoid quiet reference fields and source-plane gaps, with explicit
through-via layer changes where needed. In6 paths also avoid reference areas
under retained and newly placed bottom traces. Four existing main-ground
outlines extend around the routes. The In5 main-ground extension can overlap
the existing inlet main-ground zone to avoid an artificial seam; ownership,
quiet isolation, previous references and native fill still require checking.

plan.json is the construction input. Archived scratch scripts retain their
original temporary paths. Native DRC, ERC, parity, complete connectivity
partition comparison, copper ownership and reference review are pending.

Native candidate 03 found the old PG2 In2 segment from (133.5, 153.1)
to (133, 147.5) dangling after the old transition via was retired. This
plan explicitly retires that obsolete segment; the source group is reached
through the retained via at (133.5, 153.1). No route or field is otherwise changed.
