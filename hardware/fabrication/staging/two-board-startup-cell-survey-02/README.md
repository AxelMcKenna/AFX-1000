# U18–U28 local bypass and ground completion

The [native inventory](inventory.json) confirms that **all eleven surveyed
startup ICs, U18–U28, now have local bypass connections and both IC/capacitor
ground returns**. Eight cells are completed in this pass; U21/U25/U28 retain
their previous connections. U19's additional AUX supply pin is also joined,
and U22's two grounded inputs now reach main ground.

**None of these ICs is connected to the auxiliary regulator output source.**
Local bypass completion does not establish a powered or functional circuit.
Use the [current native project](../two-board-power-startup-remaining-native-01/power_protection.kicad_pro)
and its accompanying reviews for the exact copper and checks.

Before completing AUX source distribution, reconcile actual load states,
capacitor derating/startup demand and regulator thermal limits. The earlier
[load review](../two-board-aux-load-review-01/README.md) records unresolved
requirements; its nominal capacitor inventory predates the comparator's
additional 100 nF. Sense and timing placement and startup/fault behavior still
need review. The [named-net survey](../two-board-startup-connectivity-survey-04/README.md)
separately records 58 missing joins across 32 nets. This is not a fabrication
release or electrical/thermal qualification.
