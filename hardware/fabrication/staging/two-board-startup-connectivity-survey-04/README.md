# Startup connectivity after bypass and ground completion

The [native inventory](inventory.json) checks 91 nets containing E28_, ANA_PG
or DIG_PG, plus PWR_ALL_RAILS_ALLOW. **58 missing joins across 32 nets remain.**
This pass's 27 closures concern supply/ground connections, which are outside
that named-net selection; the surveyed startup-net join count is unchanged.

The source [power candidate](../two-board-power-startup-remaining-native-01/power_protection.kicad_pro)
has 2,172 total open connections. The separate
[cell survey](../two-board-startup-cell-survey-02/README.md) confirms local
bypass and ground completion for U18–U28, with AUX source connectivity still
missing. Native connectivity does not establish startup/fault behavior,
timing, current capacity or complete return-path quality. No fabrication
release is established by this survey.
