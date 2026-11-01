# NF04R READY integration successor

The current E28 readiness cone checks the positive rails and their sequencer PGs.
That permits host READY before the new negative-rail ramps complete. This new
NF-only schematic exports a permission that requires both completion latches
and **both protected rails' actual UV and OV checks**. A retained completion
latch cannot hide a later protected-output fault.

U44's two spare AND gates qualify each rail. Three U48 spare inverters and a
U46 spare OR combine them. New U49, an actual SN74AUP2G14DCKR double inverter,
buffers the outgoing permission; C88 is its local 100 nF bypass. J1.30 changes
from NC to `NF_OUTPUT_VALID`. All other force, fault, source, ARM, START and
MASTER connections retain their NF03C identities. There are **233 parts**.

Fresh native KiCad export has exact pin-map parity and zero ERC errors. The two
reviewed warnings are the original isolated-side U19/U24 GND1 pins, not newly
floating digital inputs. Five portable checks evaluate all64 combinations of
completion and protected UV/OV flags, unchanged active circuitry, a later rail
fault and a deliberately incorrect inverter polarity.

The proposed E28 endpoint is a new two-pin J12, with a local15 kΩ default-low
pull-down and a real Schmitt receiver. U27.3's existing readiness becomes an
internal positive-rail permission; U25's spare AND combines it with the new
conditioned negative permission and drives the existing external J9.3 identity.
**This is only the final READY leaf. It must never gate upstream MASTER, ARM or
START**, which would prevent the ramps from starting. Exact receiver pins and
native E28 adoption belong to the separate E28 owner.

`integration-contract.json` records the concrete proposed terminals, receiver
loading, AUX budget comparison and outstanding electrical checks. The new
guarded NF AUX estimate remains below the existing5 mA provision, with only
about46 µA headroom; this does not qualify the total P03 AUX pool or new E28 load.
The101 µA new-buffer Icc provision is a receiving requirement. The discrete
primary voltage/temperature rows do not establish all continuous AUX conditions.

The first231-part HCS-only export is preserved under `history/` and rejected as
a complete interface: the lightly loaded HCS voltage row cannot support a
strong default-low pull-down under the receiver's full leakage allocation.
The source NF03C remains sealed and unchanged. The active231-part PCB routing
experiment does **not** yet implement this233-part successor.

Run from the repository root:

```sh
.venv/bin/python -m hardware.qualification.boards.startup_negative_circuit.ready_integration.generate
.venv/bin/python -m hardware.qualification.boards.startup_negative_circuit.ready_integration.test_ready
```

Connector selection, actual cable/PCB adoption, threshold/partial-power behavior,
fault timing, installed fit and physical qualification remain open. No board
fabrication or production release is asserted.
