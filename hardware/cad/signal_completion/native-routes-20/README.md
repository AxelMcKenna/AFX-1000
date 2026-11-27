# Diode supply via clearance

The 0.30 mm supply-via drill at A_D101 pin 2 intersected the solder-paste land by 0.12 mm. Moving the via from (74.52, 66.075) to (74.22, 66.325) mm leaves 0.18 mm between the drill edge and the closest SMD copper. The 5 V supply uses a 0.20 mm front trace, its existing 0.60 mm inner feed and a short 0.25 mm bottom trace to the diode pad center.

KiCad confirms that the via, the diode pad and all three traces are connected. All named pad groups match the previous layout after refill. The ground changes are local to the moved via on In1.Cu, In4.Cu and In6.Cu. Neighboring signal traces retain their adjacent ground coverage.

The layout has 118 open connections, zero geometry DRC violations and zero ERC findings. Schematic parity still reports the missing A_U201 footprint. The paired footprints and mechanical outlines match the assembly capture.

[Via geometry and refill measurements](via-review.json) · [Connectivity and board hash](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
