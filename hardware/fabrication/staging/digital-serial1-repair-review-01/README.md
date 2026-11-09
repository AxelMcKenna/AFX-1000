# SERIAL_1 repair investigation

The verified digital comparison remains at **31 open connections**. No board
from this investigation has been adopted. Native board checks, 145 prior tests
and physical evidence remain in the [31-open checkpoint](../digital-bypass-ground-signal-native-02/README.md).

## What changed

The initial twelve-object repair area covers MCU_PERMIT, CLOCK_5V and LED_48.
It provides local exits but does not connect the two serial endpoints.
A wider, source-bound search identifies two additional CONTROL_30 front-layer
tracks: `0350a0fb-3e7b-5b9d-b3c0-3cd88afeda49` and
`b6609b81-ac87-5baf-b63d-5d9e5c0084c7`. Removing both in the diagnostic opens
a potential serial path; restoring either closes it in the tested geometry.
Supply/ground copper is retained in this reduced result.

Sparse nearest/centroid via samples returned no compatible receiving-end
escape triples. They missed legal original via positions. A
0.05 mm grid over x=70–75, y=17.5–22.5 mm finds **102 compatible triples**;
18 spatially distinct arrangements pass a fresh mutable-screen replay.
This proves local compatibility only. Every continuation and retired connection
still needs restoration and native verification.

The source-side restoration search identifies LED_37 via
`4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1`, at (44, 21.225) mm, as one potential
MCU_PERMIT obstruction. Trials explicitly require reconnecting LED_37 between
its front and In3 copper if that via is retired.

The receiving-side restoration search narrows a second obstruction to LED_50
track `f1ea2e26-acf3-46e4-a518-bdb380e99c7e`: In3, (73.5, 21.598) to
(77.3771, 17.7209) mm. Its omission permits an LED_48 continuation after the
local escape reservation. Restoring LED_50 remains an explicit task.

A versioned continuous-route helper skips zero-length legs at existing vias.
The previous helper could pass a one-point path to Shapely when its native
screen rejected zero-length segments. Tests now use the stricter behavior and
cover both source and destination vias, plus the four prior routing cases.
Seven additional tests check the escape-packing clearance rules. The focused
suite passes **35 tests**; see [test log](focused-tests.log).

## Evidence and limits

- [Conditional two-track CONTROL_30 result](../digital-serial1-target-cutset-02/diagnosis.json)
- [Dense local escape combinations](../digital-serial1-dense-escape-survey-01/diagnosis.json)
- [MCU_PERMIT obstruction survey](../digital-serial1-permit-obstruction-survey-01/diagnosis.json)
- [Single-object LED_48 obstruction survey](../digital-serial1-led48-single-obstruction-01/diagnosis.json)

All geometry omissions are diagnostic and require complete restoration before
adoption. No component, source board or native rule was changed. New-route
planning retains 0.20 mm width, the 0.20 mm native clearance rule, 0.60/0.30 mm
vias, and the previously declared 0.001 mm planning margin. No fabrication,
stack/process, timing, thermal, EMC or installed-unit qualification is claimed.

The exploratory (110, 55) mm probe in the earlier region report lies within the
clearance area of a supply pad. Its false results are not evidence that an
endpoint lacks access to the rest of the board. Likewise, the earlier broad
extent test's supply exclusion was only its explicitly listed net names; the
final CONTROL_30 reduction additionally protects V3V3_IO.

All search failures are bounded results, not proof that a legal layout is
impossible. Long serial-only proposals around 338 mm are neither complete
repairs nor electrically qualified routes. Final trial outcomes and source verification are recorded below.

## Next repair

Keep the compatible local escapes and the successful MCU_PERMIT continuation
as explicit constraints. With CLOCK_5V and LED_48 restored, diagnose SERIAL_1
against the resulting full copper geometry; with SERIAL_1 connected, diagnose
LED_48 against that full geometry. Further receiving-end work must satisfy
both routes at once. The BLANK_5V_SRC omission experiment supplies one wider
area to investigate, but its restoration has not been demonstrated. A legal
local escape alone is insufficient acceptance evidence.

The latest full-component target searches include sampled interior points on
retained copper, not just the ends of removed segments. This avoids treating a
single attachment point as the only possible reconnection. Native pad-group
replay remains mandatory for any future candidate. Serial path length and via
placement also require improvement and electrical review before selection.

## Completed trials

| Search | Attempts | Complete repair |
| --- | ---: | --- |
| [digital-serial1-joint-repair-01](../digital-serial1-joint-repair-01/diagnosis.json) | 6 | No |
| [digital-serial1-joint-repair-02](../digital-serial1-joint-repair-02/diagnosis.json) | 12 | No |
| [digital-serial1-packed-repair-01](../digital-serial1-packed-repair-01/diagnosis.json) | 69 | No |
| [digital-serial1-packed-repair-02](../digital-serial1-packed-repair-02/diagnosis.json) | 37 | No |
| [digital-serial1-packed-repair-03](../digital-serial1-packed-repair-03/diagnosis.json) | 48 | No |
| [digital-serial1-packed-repair-04](../digital-serial1-packed-repair-04/diagnosis.json) | 33 | No |
| [digital-serial1-packed-repair-05](../digital-serial1-packed-repair-05/diagnosis.json) | 32 | No |
| [digital-serial1-packed-repair-06](../digital-serial1-packed-repair-06/diagnosis.json) | 27 | No |

Every search has terminated. None emitted a board. The latest trials can
restore MCU_PERMIT, CLOCK_5V and LED_48 together, but the tested continuations
then block SERIAL_1. Reversing the order leaves LED_48 disconnected. This
remains a joint routing problem, with no accepted reduction from 31 opens.

[Bound review](review.json) and [recursive source verification](source-audit.json)
preserve the search history and the previous verified checkpoint.
