# DAC resistor placement clearance

Moving A_R308 by 0.30 mm along board Y increases its modeled clearance to A_R320 from 0.10 mm to 0.40 mm. The two resistors serve the left and right DAC receiver circuits. [Placement measurements](component-placement.json)

KiCad verified all previous pad connections and identical filled copper on every layer after refill. The board has 30 opens, zero geometry violations and zero ERC findings. A_U201 still needs the ES9292QPRO land and stencil dimensions. [Connectivity](native-review.json) · [DRC](drc.json) · [ERC](erc.json) · [Paired mechanical comparison](placement.json)

The trace and via geometry is unchanged from the [previous electrical layout](../native-routes-97/README.md).
