# Power-board interface reconciliation

The [source-bound review](interface-review.json) checks **30 proposed pin pairs**
against the exact six power/protection source netlists used by the two-board
placement. These are proposed electrical interfaces, not completed schematic
joins, routing, current-path qualification or a fabrication release.

Seven prohibited direct joins remain absent from the proposal. In particular:

- P03 negative rails must pass through NF before reaching E28. The older direct
  P03-to-E28 harness schedule would bypass that startup-protection stage.
- NF control raw5 must come from FPC J401's current-limited output. The older
  direct P03 raw5 proposal bypasses the added U401 protection.
- The fan-health circuit remains in series with the E28 RUN request.
- NF's separate module-input return is not automatically joined to NF AGND.
- Source and protected 5 V rails remain distinct.

NF GLOBAL_MASTER cannot be mapped to the similarly named E28_MASTER_ENABLE.
The current contract calls for a qualified buffer from **E28 U12.11
ALL_RAILS_ALLOW**; U29.7/J6.2 is a different signal. The integrated buffer,
clamp, OV-sense, fault-request, auxiliary and protected-output feedback paths
still require circuit design and loading/fault review. The NF J6 guarded module
feed and separate force return also remain unresolved.

This review preserves actual endpoint names where the two sides differ. It
does not infer equivalence from names, adopt legacy harnesses, or qualify the
large board's local placement and copper capacity. The full power schematic,
cross-board interface, thermal/airflow design and installed wiring remain open.
