# Docker absence-message recovery fix

The capacitor-move diagnostic exposed a real recovery defect: Docker returned `error: no such object: <container>`, while the workflow recognized only uppercase `No such`. The runtime now accepts explicit case-insensitive missing-object/container messages in both terminal-result and abandoned-process recovery paths. It still requires a nonzero inspect status for absence, or a successful `false` running-state response. Permission errors, unavailable daemons, missing images, live containers and unrelated diagnostics remain rejected. Recovery archives evidence and never launches CAD.

The 39 workflow/staging tests pass. The new regression exercises nine Docker replies across both recovery branches (18 cases), checks preserved failure evidence and verifies that recovery performs only the inspect call. Existing live-process checks remain in place. Self-review examined both branches and confirmed that the change neither converts uncertain status to termination nor performs an automatic retry.

The runtime source hash changes, so historical native passes are not reused as proof for this runtime. A complete check of the unchanged 86-role, 169-check selected assembly is running; completion has not yet been claimed. `selected-manifest.json` freezes the selection being reverified. Historical evidence remains untouched.
