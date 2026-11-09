# TBP59 NF control routing candidate

Four additional logic connections reduce power-board opens from 2,130 to
**2,126**, following the [TBP58 ground-reference repairs](../two-board-power-nf-logic-ground-native-02/README.md).
Open the [KiCad project](power_protection.kicad_pro).

N12_COMPLETE_CLR_N, GLOBAL_VALID, NF_OUTPUT_VALID_HCS and N19_SAFE now have
their declared connection groups joined. The added copper comprises 19
segments and eight conventional 0.60/0.30 mm vias. Each route uses front-layer
escapes and In2 routing with a common In1 ground reference.

[Native checks](review.json) report zero geometry/parity/ERC errors and two
retained ERC warnings. The [independent audit](nf-logic-detour-review.json)
verifies exactly four declared connection-group merges, preservation of all
other original connections, 2,033 retained reference checks and continuous
ground coverage beneath all twelve new path sections. All eleven supply-plane
fills and seven quiet-ground networks remain unchanged. Four ground-zone
fills are updated; 43 other fills retain their original copper. The original
supply fill is retained after independently bounding the same approximately
1.16 nm native rounding difference documented in TBP58.

Six native copper detail views were [visually inspected](visual-review.json).
The [updated NF survey](../two-board-nf-logic-reference-survey-03/survey.json)
records 43 missing joins across 39 selected open NF logic nets, with no
uncovered centers among their 98 pads. Center coverage does not guarantee a
clear escape or complete signal path.

**Not ready for fabrication.** The signal board retains 251 opens. Complete
routing, the approved codec footprint, AUX distribution, power/startup/thermal
qualification, installed housing fit, accepted stackup, final BOM and reviewed
manufacturing outputs remain unfinished. These layout checks do not qualify
signal timing or functional behavior. The selected public documentation still
describes TBP50; this candidate has not been promoted or released.
