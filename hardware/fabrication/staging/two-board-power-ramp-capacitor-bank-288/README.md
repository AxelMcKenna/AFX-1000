# Negative 12 V ramp capacitor bank

N_C43 sits beside N_C49 on the front layer. Its two 0.40 mm traces connect it in parallel with N_C42, N_C45, and N_C49 on N12_CR_TOP and PWR_N12_POST_NF. Both traces have continuous ground coverage and add no vias. The larger ramp network still requires connections to the series resistor and the rest of the bank.

KiCad verified both intended pad-group joins. The power board has 886 remaining open connections. [Capacitor placement](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
