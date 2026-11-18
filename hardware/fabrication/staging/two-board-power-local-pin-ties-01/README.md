# Power/protection local pin connections

This KiCad candidate adds 21 front-copper connections to TBP73. Four connect AUX pins 7 and 8 on N_U1, N_U2, N_U7 and N_U8. Twelve connect local address, enable, serial-input and threshold straps on N_U18 and N_U23. Five connect the inactive reset input to its local supply on N_U20, N_U21, N_U25, N_U26 and F_U9.

All additions are single 0.30 mm tracks between pins of the same component. The board retains all TBP73 footprint positions and saved zone fills. Each added copper span between the original pad lands falls over connected In1.Cu main ground in the TBP73 native geometry capture. The route manifest records both pin identities, geometry, UUID and uncovered area for each connection.

KiCad 10.0.7 reports 1,915 open connections, down from 1,936. Native pad connectivity matches the expected partition after the 21 joins. DRC with zone refill and schematic parity reports zero geometry and parity findings. Its unconnected-item list is capped at 499 entries. The uncapped native count and board hash are in [connectivity.json](connectivity.json).

The local straps do not complete regulator feeds, establish load capacity, or qualify startup behavior. The candidate uses the provisional stackup and remains in development.
