# Current hardware designs

The latest verified power-board working candidate is [TBP63](../staging/two-board-power-ready-return-planes-native-01/final-review.json).
[TBP50](../staging/two-board-fabrication-status-50/status.json) remains an earlier recorded selection.
Neither board is ready for fabrication.

| Design | Editable project | Review |
| --- | --- | --- |
| Signal main | [KiCad project](../staging/two-board-signal-routed-native-03/signal_main.kicad_pro) | [251 opens and missing codec footprint](../staging/two-board-signal-routed-native-03/README.md) |
| Power/protection | [KiCad project](../staging/two-board-power-ready-return-planes-native-01/power_protection.kicad_pro) | [2,094 opens; AUX source distribution unfinished](../staging/two-board-power-ready-return-planes-native-01/README.md) |

Supporting inventories retain their own revision scope; the latest [control-return survey](../staging/two-board-control-return-survey-after-04/survey.json) covers TBP63. Earlier inventories cover [startup connectivity](../staging/two-board-startup-connectivity-survey-06/README.md),
[local startup cells](../staging/two-board-startup-cell-survey-04/README.md) and
[AUX distribution](../staging/two-board-aux-distribution-survey-02/README.md).
The [fabrication inventory](../README.md) records remaining electrical, mechanical,
manufacturing and qualification work. The earlier module-level selections in
[scope.json](../scope.json) remain reference checkpoints for the consolidation.

Browse [retained experiments](../experiments/README.md) separately. The
[workspace catalog](../workspace-catalog.json) records the earlier TBP50 selection,
module references, immediate review inputs, and retained history/experiments.
These categories organize the workspace; they do not change any review's scope.

Native designs and evidence remain at their recorded `staging/` paths so source
hashes, imported libraries and historical comparisons retain their meaning.
