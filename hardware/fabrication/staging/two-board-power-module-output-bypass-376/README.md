# Module output bypass placement

G_C2 now sits on the back of the board directly beneath clamp G_D2. The capacitor connects across the module eFuse output and its primary return. The supply and return vias are 1.23 mm apart. The four surface traces total 3.74 mm. The nearest modeled component is 3.28 mm away. The capacitor clears the touch-panel post reserve by 2.07 mm. [Placement measurements](component-placement.json) · [Route geometry](layout.json)

KiCad counted 727 remaining opens and verified every intended pad group. The isolation survey found zero package-midline crossings. The power schematic retains two ground-pin ERC warnings. [Connectivity](connectivity.json) · [Ground plane measurements](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
