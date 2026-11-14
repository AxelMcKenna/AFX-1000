# Rejected strict refill output

The native refill completed, but the strict preservation assertion rejected a changed retained In2 supply polygon (UUID `0552f897-fa23-5173-9e85-a8133b7a4048`). This folder is not an accepted PCB.

The [diagnosis](../two-board-western-logic-returns-refill-diagnosis-02/native-comparison.json) checks every non-declared fill and finds only that one bounded rounding difference. The [retention record](../two-board-power-western-logic-returns-filled-04/local-plane-fill.json) preserves all 39 original retained fills exactly and imports only the eight declared fills. The resulting [native candidate](../two-board-power-western-logic-returns-native-02/README.md) passes the subsequent geometry, connectivity and reference audits. Fabrication remains unreleased.
