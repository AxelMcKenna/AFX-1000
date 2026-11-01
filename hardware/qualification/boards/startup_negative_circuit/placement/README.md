# NF03P native placement and routing study

This actual KiCad board places all231 parts from the sealed NF03C circuit on a
149×39 mm, four-layer PCB. It is a receiving design study, with no fabrication
release. `generated/native-pcb.json` records exact physical-pad/net parity,
including the four intentionally unconnected physical TLP4590AF lead3 pads.

The N12 force components are grouped on the left and N19 on the right. Deep
module/film parts are anchored explicitly. Thirty-two actual AUX-powered ICs
have assigned rear-side0603 bypass capacitors, with at most1.543 mm projected
pad separation before routing. Actual return/via inductance remains unaccepted.
The remaining generic shunt/timing/filter parts and physical connectors require
real selections and complete package/process review.

Six DCU0008A footprints use TI's actual example land instead of the generic
library's incompatible pad spacing. A separate cosmetic footprint variant
removes external silk triangles where they overlapped neighboring silk; it
preserves all electrical geometry. These changes are recorded with original and
replacement hashes. No DRC exclusions or ignored checks are used. The fresh
private `routing/connectivity-silk/input.kicad_pcb` has zero native violations,
but499 unrouted connections before the routing experiment.

The intended world frame is X=172+u, Z=3.5+v, Y=180.5−w, with nativeu/v on the
board and positivew outward from the component-front face. FR4 lies behind
that face; a1.76 mm maximum FR4 thickness and1.0 mm rear assembly envelope reach
Y183.26, below the Y183.8 lid seat. The receiving board spans X172..321 and
Z3.5..42.5. This arithmetic does not establish complete fit: actual bodies,
tails, mates, wire bends, bosses, mounting and floor-port blockage require the
separate whole-unit assembly review. There are no implemented board mounts.

`route_io.py` exports immutable per-candidate DSN/PCB/project files and imports
Specctra sessions while checking all component positions, sides, values and
pad nets. The In1.Cu AGND plane is a connectivity proposal. Default0.2 mm signal
tracks do not qualify the negative force path, Kelvin sensing or quiet returns;
these require explicit copper resistance, current and noise review after native
KiCad DRC. Existing E28 source/output Kelvin and force connections are separate
integration work.

The first FreeRouting native executable failed on missing Graal serialization
support; its log/rejection is retained under the private routing candidate.
The Java25/JAR fallback runs on the same bound DSN with a separate private
profile, analytics/API/MCP disabled. Router results require import and fresh
KiCad checks before adoption.

The newer [NF04R readiness successor](../ready_integration/README.md) adds an
output buffer and bypass and changes spare-gate wiring. This231-part board does
**not** yet implement that233-part circuit. Standalone ARM/START generation,
module initial-power margin, E28 integration, physical wiring, protected endpoint
voltage, startup/fault behavior and installed cooling remain open.

The SVG/PDF under `generated/` show actual footprint placement. They are review
drawings, not manufacturing outputs. All physical and release flags remain false.
