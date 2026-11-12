# Current hardware designs

The latest verified power-board working candidate is [TBP72](../staging/two-board-power-aux-ground-reuse-native-01/final-review.json).
[TBP50](../staging/two-board-fabrication-status-50/status.json) remains an earlier recorded selection.
Neither board is ready for fabrication.

| Design | Editable project | Review |
| --- | --- | --- |
| Signal main | [KiCad project](../../cad/two_board_sensor_05/signal_dac/native-r26/signal_main.kicad_pro) | [198 opens and missing codec footprint](../../cad/two_board_sensor_05/signal_dac/README.md) |
| Power/protection | [KiCad project](../staging/two-board-power-aux-ground-reuse-native-01/power_protection.kicad_pro) | [1,937 opens; AUX source distribution unfinished](../staging/two-board-power-aux-ground-reuse-native-01/README.md) |

Supporting inventories retain their own revision scope; the latest [control-return survey](../staging/two-board-control-return-survey-after-08/survey.json) covers TBP67. Earlier inventories cover [startup connectivity](../staging/two-board-startup-connectivity-survey-06/README.md),
[local startup cells](../staging/two-board-startup-cell-survey-04/README.md) and
[current AUX distribution](../staging/two-board-aux-distribution-survey-06/inventory.json).
The [fabrication inventory](../README.md) records remaining electrical, mechanical,
manufacturing and qualification work. The earlier module-level selections in
[scope.json](../scope.json) remain reference checkpoints for the consolidation.

Browse [retained experiments](../experiments/README.md) separately. The
[workspace catalog](../workspace-catalog.json) records the earlier TBP50 selection,
module references, immediate review inputs, and retained history/experiments.
These categories organize the workspace; they do not change any review's scope.

Native designs and evidence remain at their recorded `staging/` paths so source
hashes, imported libraries and historical comparisons retain their meaning.
