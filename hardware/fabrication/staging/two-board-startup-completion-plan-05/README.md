# U30/U34/U41 startup interconnect completion candidate

Development candidate from TBP42; not a fabrication release. All 23 targeted
interconnects are routed, including FOLLOW3 to the existing U33 enable group.
The expected net connectivity improvement is 27 joins, accounting for five
restored connections, six main-ground joins and three local bypass joins.
All six IC/capacitor placements and component values are retained from plan 03.

FOLLOW3 branches from the retained enable via at (146.34, 128.825) on the front,
then uses two new through vias and two inner layers to reach U34.7. Both legs
of a layer transition can use a screened grid path; restricting one leg to a
simple path had missed this route. Every final path remains subject to native
clearance and connectivity validation. The prior dangling PG2 segment remains
explicitly retired. No interconnect in this targeted set remains deferred.

Four main-ground outlines extend around the routes. The existing In5 inlet
main-ground field is allowed to overlap its same-owner extension. Quiet return
fields and adjacent references beneath retained/new bottom traces remain
protected. Native fill, connectivity partition comparison, complete reference
coverage, physical review and broader startup qualification remain required.

plan.json is authoritative construction input. Archived scratch scripts retain
their temporary paths. Earlier interconnect snapshots preserve search history.
