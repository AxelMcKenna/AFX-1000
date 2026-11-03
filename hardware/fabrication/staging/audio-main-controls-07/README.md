# AC04 — short CHIP_EN bridge

**Partial routing; not ready for fabrication.** A 2.617 mm bridge connects
U210.6 to the R209.1/TP402.1 native island through one conventional
0.60/0.30 mm via. The exact shared via at (66.7,8.3) mm avoids the coarse
search grid's missed pin exits. A further CHIP_EN connection remains open.

Native Linux KiCad 10.0.7 reports **204 opens**, three remaining control gaps,
zero geometry/ERC findings and one missing U201 footprint. Every parent
component pose, unretired copper object, project and schematic remains exact;
all 138 local, 17 earlier control, 200 ground and 161 rail/sense witnesses,
both private timing pairs and the earlier global-control witnesses remain
connected. Refilled ground is taken from the actual native export.

The [source-bound handoff](routing-handoff.json) independently checks the
actual additions, hole-to-land spacing and complete native pad witnesses.
Construction checks do not qualify timing, loading, return transitions, noise
or installed fault behaviour. The [following CODEC_PGOOD comparison](../audio-main-controls-08/README.md)
retains this bridge and reaches 203 opens. The selected 208-open fabrication
snapshot remains unchanged; neither comparison is a fabrication release.
