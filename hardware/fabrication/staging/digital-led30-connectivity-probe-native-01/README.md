# Rejected LED30 connectivity trial

**Do not use this board for fabrication or as the next accepted checkpoint.**

Native KiCad checks, with all categories enabled, report **27 opens and two
track-dangling warnings**, with zero parity/ERC findings. LED30 connects,
but U3002.30 is separated from the other five LATCH pads. This is not an
improvement over the retained 27-open board, whose other findings are zero.

The warnings identify the F.Cu tip near (29.3,19.3) mm and the In3.Cu tip
from (33.2,15.2) mm. They are retained in [the native report](review.json).
The [read-only native capture](../digital-led30-connectivity-probe-inputs-27/capture.json)
explicitly retains those warnings for diagnosis; it does not waive them.

Use the [verified LED16 checkpoint](../digital-led16-closed-native-01/README.md).
See [the continuation review](../digital-routing-continuation-27-01/README.md)
for unsuccessful repairs and remaining work.
