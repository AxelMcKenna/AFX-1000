# Isolated held-driver ground returns

`native-02` adds eight 0.3 mm F.Cu tracks and two ordinary 0.6/0.3 mm ground vias to the held-cutover candidate. Five formerly singleton pads now join the existing main ground: E_C29.2 and E_U1/U2/U3/U4.4. Native opens fall from 1964 to 1959; these are candidate counts, not the accepted PCB count. Every other original group membership, pad identity, copper object and complete zone/fill is retained. All 55 formerly anonymous source pads retain their unique full physical identities.

Si8751 GND is pin 4. The prior `routed/bypass.py` distance audit mistakenly used TT pin 2 as return. That audit and its JSON are corrected in this checkpoint. No prior routed copper used this mistaken return pin: previous supply branch edits only used VDD pin 1. Regression coverage rejects routing the TT pin as ground.

The C29 return begins inside the actual pad at (47.952080, 111.485733), rather than its center outside the In1 main fill. The complete added 0.3 mm track is referenced by the existing main fill, including its start disk; native connectivity proves actual pad contact. Its 5.35 mm route and U1's 4.67 mm return establish connectivity but do not establish a low-inductance local bypass loop. U3's return is 4.91 mm. U2 and U4 have short 0.70/0.45 mm returns to new vias with actual native main-plane contact. All new copper avoids the retained quiet-pass objects, including already main-connected quiet ground tracks, and all seven quiet plane outlines. No zone is expanded or refilled.

`native-01` is a rejected local experiment, not part of this checkpoint: its shorter U1 route used a retained quiet-pass ground object. `native-02` routes around that object, and independent geometry checks reject such contact even when the object's logical ground group is already main connected.

C36 remains unconnected after the bounded surface and all-layer-via search. U4/C13 local placement and positive branch revision remain pending; existing shared AUP and LDO branches remain pending cutover. No placement changes or positive branch changes occur here. Large positive/return loop dimensions still motivate local capacitor repositioning.

The four native TPS3703 DSE clearance errors remain exactly unchanged and unwaived. No clearance rule, accepted PCB or fabrication status is changed. Native DRC reports a capped list of 499 unconnected items; 1959 is the uncapped native count.

The prior electrical receiving conditions remain unresolved: ≥200 µF effective reservoir, ≤100 mA drain, ≤20 mV distribution drop and ≤1 µs logic delay allocation. Under those conditions the modeled hold interval is 81.00348 µs and the remaining driver turnoff allocation 50.00348 µs. These routes do not establish actual current, transient/reset timing, capacitor effectiveness, thermal performance or safe startup/recharge.

Verification: `python -m hardware.qualification.two_board_aux_current_08.held_loops.verify`; four tests in `held_loops.test_verify`. Native execution uses the established pinned Linux KiCad image with read-only input and isolated output. The source-bound capture includes complete native groups and raw/unfractured zone data; its point/area fidelity is retained for subsequent routing.
