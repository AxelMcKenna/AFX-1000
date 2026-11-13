# PD via diagnostic r138 — never a routing candidate

This diagnostic temporarily removes exactly the three parent-authorized obstacle tracks and inserts a PD_R via at (75.8,77.65), without replacement routes. It is not electrically acceptable and must not be selected. Its purpose was to test whether the conservative 0.63 mm pruning estimate actually removed original NBIAS_R reference support.

The pinned native refill saved diagnostic-only.kicad_pcb, then hit a KiCad SWIG object-lifetime error while exporting fields. A separate pinned read-only recapture read that saved file without repeating the fill. The source-bound review reports zero raw NBIAS_R reference loss. Subsequent candidates must independently prove complete replacement routes, native geometry, reference support and physical returns.
