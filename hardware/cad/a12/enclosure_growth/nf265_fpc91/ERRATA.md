This packet preserves the first receiving trial and its rejected geometry.

The NF source's KiCad JSON lists 499 unconnected items because that report is capped. Root independently counted 750 using the native connectivity graph. The captured source is unrouted; 499 in the initial capture/native metadata is a capped **report count**, not the complete graph count or an electrical closure claim.

The first tail model inherited FR01's square envelope, using the larger native pad dimension for both lateral axes. The separate `tail_shape/` model retains each actual rectangular pad dimension and absolute angle, plus the same 0.2 mm allowance per lateral side and 1.5 mm rear trim/fillet requirement. Every new tail receiver is contained in the earlier envelope. No source pad, part pose, copper, mating receiver or allowance changed. TMR pads are actually 1.5 × 3.0 mm, long along native V; this correction **does not clear** their rear-capacitor receiving conflict. The initial 3.0 × 1.8 mm orientation hypothesis was incorrect.

The FPC C401/C402 courtyard conflict is retained. A separate native check uses their primary KEMET maximum body L1.75/W0.95/T0.95 mm plus the declared 0.1 mm seat, at the actual B-side 90° poses. Those bodies clear C203.2's retained pad/fillet tail receiver even with a stronger 0.45 mm relative-position-plus-clearance comparison. This establishes that local body comparison only; supplier/process, complete board and harness qualification remain false.

The zero-volume `new_mount_mates_collision` STL is rejected, not an empty pass. It lies at the expanded unselected ISP receiver's Z40.3 boundary and the keeper's Z40.3 lower face. There is no new contact guard or tolerance waiver. A selected service plug and actual body/standoff contract are still required.
