# LED driver channel 01

D_U3001 pin 6 now reaches D_J3003 pin 2. The breakout reuses an inner trace that previously served LED_00. LED_00 has its own path to D_J3003 pin 1. LED_04 takes a new approach to D_J3003 pin 5 with 45-degree bends. The schematic pin assignments stay the same. KiCad verified the one intended pad-group join and all previously connected pad groups.

The new 0.20 mm routes use three signal vias. Their ground stitching vias lie within 1.46 mm. Two new ground vias sit 1.95 mm and 2.54 mm from the retained transitions. Each routed leg has a continuous ground reference outside its via and terminal clearances.

The digital 5 V pour remains one connected region. With 96 mA per header, the largest modeled header drop is 5.218 mV on the 0.065 mm mesh. The largest increase relative to revision 94 is 0.024 mV. LED switching noise and header voltage still require bench measurement.

KiCad reports 31 open connections, zero geometry violations and zero ERC findings. A_U201 remains absent pending the ES9292QPRO package dimensions.

[Routing changes](route.json) · [Ground coverage](reference-review.json) · [Return paths](return-islands.json) · [5 V distribution model](power-sheet.json) · [Adjacent copper](coupling.json) · [Connectivity](native-review.json) · [Enclosure comparison](placement.json) · [DRC](drc.json) · [ERC](erc.json)
