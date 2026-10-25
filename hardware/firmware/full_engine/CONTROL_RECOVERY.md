# F06 control recovery

`main.cpp` integrates `ControlRecovery.h` and `ControlReset.h` before foreground control dispatch. These are software input/recovery guards. They do not arm processing, replace an independent hardware interlock or establish physical timing. The F05 snapshot is unchanged by this F06 extension.

## Complete-frame validation

The earlier loop dispatched button edges before validating release-selector contacts and the scheduled touch read, and ran long-action `tick()` even when input health was false. A failed later read could therefore leave a pad, modifier or scene action already queued. A held input could also restart a gesture or fire on release after a bus fault.

The F06 loop now gathers buttons, angle and any scheduled touch sample before dispatch. `ControlRecovery` caches a failed touch read until a fresh valid sample; an iteration that does not read touch cannot repair that failure. Cached touch data expires at the existing 20 ms control-freshness limit. Conflicting raw Back Spin/Brake contacts invalidate the complete frame. The debounced selector combination is checked again before button actions; rejection cancels the frame rather than ignoring `releaseSelection()`'s result.

Both the interval between foreground polls and the elapsed duration of the current I/O frame are checked against that same 20 ms limit. A foreground block-counter monitor detects a stopped audio callback at the same boundary, even if control reads continue succeeding. This supplements the independent watchdog; it is not a replacement or a measured timing guarantee.

## Held inputs and re-prime

The gate requests one gesture clear on the first fault in an episode. A complete valid recovery snapshot re-primes without dispatching actions. All 29 momentary button bits held at boot/recovery are masked until each is continuously released for the existing 5 ms debounce interval. Persistent Default/User and Release selectors retain their physical positions. Held touch stays blocked until a fresh valid inactive sample; a lever held across boot/recovery waits for its existing calibrated home threshold.

The actual foreground re-prime waits for the callback to acknowledge a priority DSP reset. It then primes the Debouncer with sanitized momentary keys, reconstructs the foreground-only Controls object, initializes its buttons as released and takes fresh first knob readings. Clearing knob `seen`/history state prevents a post-fault depth reading from engaging Scene FX. Waiting for acknowledgement is essential: Panic zeroes Low/Mid/High, so applying the first physical band readings before Panic would leave those bands wrong until the knobs moved again.

Only dispatch-enabled frames run button actions, normal knob updates, touch updates and long-action `tick()`. Touch calls occur only for a freshly sampled valid update. Calibration chords use sanitized/debounced keys, so boot/recovery-held modifiers must be released before starting a new chord.

## Priority callback reset

`PriorityControlReset` uses generation tickets and acknowledgements. The foreground can request a clear without relying on the Engine event queue. The audio callback snapshots a ticket and, when needed, supplies an offset-zero direct Panic event to `Engine::process`. The maintained Engine consumes queued events before this direct event and before its first output sample. A full queue can reject an ordinary enqueued Panic; it cannot reject this direct event.

The callback acknowledges only the ticket it actually processed. A request arriving while DSP runs remains pending for a later callback. Processing permission is denied while a reset is pending and during a callback that executes a reset. Foreground eligibility also requires reset completion and completed control re-prime.

A callback-observed fresh-to-stale transition requests a reset and notifies the foreground to invalidate/re-prime its input state. An unchanged stale episode does not repeatedly Panic after acknowledgement: repeated Panic would erase newly restored physical bands while the foreground was preparing its first healthy timestamp. Callback freshness is checked both before DSP and again before relay permission. If the latter check crosses the deadline, another reset remains pending for the next callback.

If callback preemption changes the reset generation while foreground actions or re-prime run, or the frame becomes late, the foreground cancels that frame and issues another reset. This clears any actions produced after an earlier reset completed. These guards preserve the existing converter, actual-input-quiet qualification, callback warm-up, calibration, physical bypass, 350 ms stable rearm and relay-feedback requirements.

Panic is a deliberately conservative fault policy: it stops voices/rolls/nudging and also clears the recorded sequence, scene engagement and isolator bands. It is not a transparent pause that preserves recording. A separate engine command would be needed for a less destructive recovery policy.

## Calibration frame cancellation

The second calibration point first disables processing/audibility, resets the recovery/rearm state and requests a priority clear. If audio stop fails, it latches an audio fault and skips both the QSPI write and a second audio start. A successful stop permits the existing checked calibration save. The callback warm-up counter is reset and external qualification restarts silently as before.

After attempting audio restart, the loop immediately continues. The old touch, angle and debounced-key snapshot cannot then reach knob, touch or long-action dispatch later in the same frame. Subsequent recovery requires an acknowledged reset and fresh re-prime; a still-held calibration chord is suppressed until released. The original QSPI sectors and calibration validation are unchanged.

## Checks

The existing `full_control_recovery` CTest group covers all 29 momentary bits; boot/fault-held buttons, touch and lever; release chatter and independent keys; invalid selector/angle/rear/button frames; cached touch failure/staleness; nonfinite/out-of-range active coordinates; repeated faults; callback progress; reset-ticket acknowledgement; and uint32 timer/block-count wrap at the exact 5/20 ms boundaries.

The existing `full_integration` group additionally fills the actual maintained Engine queue with pad events, verifies an ordinary Panic enqueue fails, then verifies a direct offset-zero priority Panic produces no queued-pad output and clears gesture state. It checks newer reset requests are not acknowledged by older tickets and that physical bands restored after acknowledgement persist without engaging Scene FX.

```sh
cmake --build build/full-engine-host --target full_control_recovery full_integration --parallel 4
ctest --test-dir build/full-engine-host --output-on-failure \
  -R '^(full_control_recovery|full_integration)$'
```

The gate tests also pass standalone with `-Werror`, AddressSanitizer and UndefinedBehaviorSanitizer. The final main integration still requires the clean dual-profile ARM rebuild and updated validation record owned by the main integrator. Electrical inputs, actual interrupt/callback timing, relay behavior and the complete physical unit remain unqualified.
