# Via clearances to mask and paste openings

This check measures the nominal edge of each through-via drill against the nearest opening in the four KiCad Gerber plots. Distances below are in mm. All 2,107 drills clear the plotted openings on both faces. [Signal board](../../../cad/signal_completion/native-routes-37/signal_main.kicad_pcb) · [Power board](../two-board-power-digital-source-status-75/power_protection.kicad_pcb)

| Board | Vias | Front mask | Back mask | Front paste | Back paste |
| --- | ---: | ---: | ---: | ---: | ---: |
| Signal | 1110 | 0.1200 | 0.1026 | 0.1253 | 0.1026 |
| Power | 997 | 0.1246 | 0.1250 | 0.1641 | 0.1640 |

Both boards specify eight copper layers and 1.6 mm thickness. All via drills are 0.30 mm. The 0.60 and 0.65 mm lands provide 0.15 and 0.175 mm nominal annular rings. On the signal board, 21 vias meet thermal ground lands under D_U3001, D_U3002 and D_U3003. Their drills clear the separate paste deposits and mask openings. Supplier review still needs to establish finished-hole tolerance, registration and tenting capability for this stack. [Signal lands](signal-lands.json) · [Signal plotted openings](signal-openings.json) · [Power lands](power-lands.json) · [Power plotted openings](power-openings.json)

## Reproduction

Run from the repository root with the editable board path in `board`. Use an empty directory in `plots` for each board. The land check uses KiCad 10.0.7 Python bindings. The plot check uses Gerbonara 1.6.3 and Shapely 2. Files record the board SHA-256, nearest via and signed clearance for each film.

```sh
review=hardware/fabrication/staging/two-board-via-assembly-review-01
kicad-cli pcb export gerbers --layers F.Paste,B.Paste,F.Mask,B.Mask -o "$plots" "$board"
python3 "$review/measure_lands.py" "$board" "$plots/lands.json"
PYTHONPATH=. python3 "$review/measure_openings.py" "$board" "$plots" "$plots/lands.json" "$plots/openings.json"
```
