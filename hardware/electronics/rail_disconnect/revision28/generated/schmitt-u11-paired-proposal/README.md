# Independent paired U11 receiver restoration — source-specific partial proof

Use `final-paired/`, `final-delta-proof.json`, `final-comparison.json`, `final-drc.json`, `final-erc.json`, `final-netlist.xml` and `final-schematic-proof.json`. Earlier `candidate2-paired`/native report is a rejected intermediate; `candidate3-paired` is the working intermediate before restoring the original P19 buffered trace width. Original independent candidate0 and its68-file seal remain unchanged.

SourcePCB is b922460f8129094b9760e5eb229602b83013f82248d56c82d9b4f85200a1d967 from `schmitt-u37-backbone-clear-work` (base41opens). Final native-refilled PCB is c43c6cac0cf82e33ecde576ae98499a650a1932ea3b84d201c9826c6a1f1b9e9. This is not the owner's later coherent routing source, and its pass cannot be inherited after merging.

The stronger repair commutes ONLY the two inputs of actualU11AND2: pin4 becomes N12_OV_OK_SCHMITT and pin5 becomes P12_OV_OK_SCHMITT; output6 staysOK_12. ExistingAND1commutation/pins1/2 remain unchanged. Both schematic labels, componentJSON and physical PCB pad-net bindings were changed consistently;269 actual exported native components/pins/values match, ERC0 and schematicparity0. All256combinations of the eight independent OV/reference conditions produce identical fourAND outputs; a deliberately wrong cross-gate mutation is detected in96cases. Producer/comparator/hysteresis nets remain unchanged; this is solely receiver input commutation.

The new N12 receiving barrel is local(7.500,14.075), .6land/.3drill, filled/capped receiving process. It has a direct .2F stem from upper U11.4. Lower U11.5 has a deliberately routed .2F path to the preserved P12 receiving barrel(6.75,14.6). U36.2B is rejoined to that same oldbarrel, and N19rawU36.3B is rejoined to the retained leftBtrace. Two original P19buffered In3 corner segments(.25wide) are replaced by one direct diagonal **at the same .25width**, avoiding the newly proposed barrel. All1447originalvias and all273physical footprint geometries/properties remain exact, apart from the declared two U11 pad-net bindings and native-generated missing UUIDs.

Relative to the exact original source, the finaldelta removes40 source controlsegments and adds17segments/onevia. Exact original UUID/fullobject removals and final addedobjects are in `final-delta-proof.json`:

- P19buffered:2removed,1added diagonal.
- P12buffered:25removed,8added F/Bsegments.
- N19raw:12removed,7added Bsegments.
- N12buffered:1oldstubremoved,1newFstemadded plusnewbarrel.

No force, quiet-sense/reference, GND track or existing via was removed. Every native geometric rule remains unchanged. The local search's optional20µm computational guard is not a board rule; final segments were checked against the exact .2mm native clearance. Minimum source/etch/drill/registration/process bounds are not established.

Native whole-board results under the same inherited profile:

| Scope | Hard | Warnings | Opens | Parity | ERC |
|---|---:|---:|---:|---:|---:|
| Fresh source baseline | 0 | 152 | 41 | 0 | original source |
| Finalpaired successor | 0 | 151 | 41 | 0 | 0 |

The same five stock checks remain ignored and are explicitly recorded in rawJSON; no all-check/fully-routed acceptance is claimed. P12buffered's two real native pads(U11.5/U36.2) and all fourN19raw pads(U9.1,R63.1,R64.2,U36.3) no longer occur in native opens. **N12buffered still has its original onward open U11.4→U37.7** on this oldsource; the owner's new U37 backbone/receiving escape must be joined and natively checked on its coherent source. This is not an all-three-net closure claim.

Fresh actual native-fill comparison withdraws AGND0.774496mm² onIn1 and0.730745mm² onIn4, with small recorded additions; no other net/layer delta exceeds1e-7mm² in this diagnostic. Shapelymake_valid was applied to128 native fractured/keyhole polygons in each board. This is a saved-fill geometric comparison, not a resistance/return/noise bound. Full coupled ground/force/thermal/material/temperature extraction must be renewed after the owner's actual merge.

Rejected exact suggestions are retained: newP12barrel(11,14.5) conflicts with24 literal track obstacles including quietN12_OV_SENSE; its handFstem also hitOK_12 and the Bdiagonal hit realU36.1. The first7.6,14 N12relocation failed nativechecks against retained P19In3 and P12/N19B controlpieces. None was forced by shrinking a footprint, moving an oldvia or relaxing a rule.

Apply only the declared source-derived delta to a NEW coherent ownercandidate after verifying source/local object equality. Do not overwrite the owner's full board. All physical, process, PDN, noise, fully-routed and adoption flags remain false.
