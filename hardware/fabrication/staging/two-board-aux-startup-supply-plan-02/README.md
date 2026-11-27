# Retained startup-cell supply routing screen

This checks the current TBP72 supervisor E_U19, reset buffer E_U35 and bypass
E_C78 supply islands. All selected pads are on B.Cu. The AUX redesign retains
these footprints and supply connections, so this work is independent of the
candidate regulator/divider values.

No accepted route was found in this bounded surface-only screen. The first pass
(`../two-board-aux-startup-supply-plan-01/plan.json`) checks direct, orthogonal,
45-degree and offset doglegs to existing source-group copper and local bypass
pads. The second adds up to three source-target grid searches per IC, each
limited to12,000 nodes. Width is0.3mm; no new via, plane change, component move or
PCB edit was made. Failure here does not prove the connection is unroutable.

Both screens retain the existing mount, copper and keepout exclusions. New trace
bands require full anchored adjacent In6 ground coverage; surface changes also
avoid previously covered adjacent inner-track reference bands with the inherited
0.435mm clearance/plane-width allowance. These are conservative planning rules,
not native signoff.

E_C78.1 has an additional endpoint obstacle: its pad center is0.024517mm outside
the anchored In6 main-ground fill. A0.3mm starting disk has0.042603mm² uncovered.
Consequently no path starting at that pad center can satisfy this screen's full
reference rule. The next design step must explicitly distinguish pre-existing
pad copper from newly added trace, verify a valid referenced pad escape, or
change the local ground/placement design. Merely increasing the search budget
cannot resolve that endpoint condition. Existing-via endpoints similarly need
proper transition evidence; no blanket reference exception is introduced here.

The two planning scripts and JSON artifacts bind their native input capture and
helper sources. Any future authored copper requires native refill, DRC, exact
connectivity/group preservation, mount clearance and new/retained reference
verification. Current power routing remains TBP72 with1,937 open connections.
