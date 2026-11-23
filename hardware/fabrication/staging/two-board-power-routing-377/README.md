# Negative-rail undervoltage comparator

N_U15 pin 8 now reaches the junction of N_R43 and N_R44. The 0.85 mm front trace connects to a through-via at the divider tap. Both resistors reach that tap on the back. A ground via 2.48 mm away connects the adjacent front and back reference planes. [Route geometry](layout.json) · [Ground plane measurements](plane-review.json)

KiCad verified the intended join and every other pad group, and counted 723 remaining opens. All eight copper layers refill reproducibly. The new via clears both ground planes locally and its antipad reaches the edge of N_R43 pad 2. The pad center retains its reference. Copper under unrelated routes is preserved. Both board placements match the enclosure capture and the surveyed isolation-package midlines remain clear. The power schematic retains two ground-pin ERC warnings. [Connectivity](connectivity.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
