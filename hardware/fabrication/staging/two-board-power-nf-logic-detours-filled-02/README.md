# Refill stopped at exact preservation check

This directory is **not an accepted PCB candidate**. The strict retained-zone
comparison stopped on the module-feed supply polygon's numerical difference.
The [native diagnosis](../two-board-nf-detour-refill-diagnosis-01/native-comparison.json)
records the difference. The [retained-fill candidate](../two-board-power-nf-logic-detours-filled-03/local-plane-fill.json)
keeps all 43 original fills exactly and uses native refill only for the four
declared ground zones. The independently reviewed design is
[TBP59](../two-board-power-nf-logic-detours-native-02/README.md).
