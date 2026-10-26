# Performance controls

The main surface follows the RMX-1000 layout. The amber and teal skin and RMX badges distinguish this project. These are original algorithms; an equivalent control layout does not establish an equivalent sound.

| Control | Software behavior |
| --- | --- |
| Input / Output level | Drag vertically; Shift makes fine changes. Double-click or right-click for an exact value. |
| Quantize | Align repeat/roll starts to the selected beat grid. Pad one-shots remain immediate. |
| Auto | Follow the host/MIDI tempo in the plug-in, or analyze incoming audio when no external clock is available. Switch off to hold manual BPM. The button pulses while confidence is low. Detection targets 70–180 BPM; half/double-time ambiguity remains possible on music. |
| BPM display | Drag or double-click to enter manual tempo, 40–240 BPM. Switch Auto off for manual control. |
| Tap | Tap in time at least twice. Tempo averages up to four valid tap intervals and disables Auto. |
| Nudge − / + | Press and hold to advance/delay X-Pad timing without changing the stored BPM. Accessibility activation applies one small timing step. The current 2% hold rate still needs reference-unit calibration. |
| Input / X-Pad source | Independently include or exclude each source from the effects. Both may be off. Selection applies to Release FX too; Noise remains available with both off. |
| Isolator / Cut-Add / Trans-Roll / Gate-Drive | Select and enable the band processing mode; press the selected mode again to bypass the section. Low / Mid / Hi control their respective bands. |
| Scene FX ring | Select an effect; press the selected effect again to bypass Scene FX. |
| Large Scene knob | Control the selected effect: filter cutoff, echo/reverb balance, crush amount or spiral delay window. Moving it enables Scene FX. |
| Sub parameter 1 | Echo selects one of four time regions. Factory BPF/HPF/LPF/Crush Echo crossfade between adjacent times. Effects retain independent User beat assignments. In Noise it changes generated-noise level, and in reverbs it changes reverb level. |
| Sub parameter 2 | Adjust the effect-specific filter, modulation or pitch control. See the [DSP control table](dsp-model.md). |
| Bank | Select bank samples, then cycle through four banks. Shift-click returns to internal drums. Bank indicators are dark while internal drums are selected. |
| Roll | Select live-input roll instead of the sample bank. |
| Kick / Snare / Clap / Hi Hat | Trigger the selected sound immediately and select sample playback. Number keys 1–4 do the same. Shift-click deletes its recorded lane. Option/Alt-click selects silently when Overdub is off, or toggles its recorded-lane mute when Overdub is on. |
| X-Pad strip | Eight positions repeat the selected sound at their assigned divisions. Set **X-Pad position 1–8 beat** in User settings; choices include triplets and range from 1/32 to eight beats. The strip displays the effective assignments. Live-input roll records from the touch and repeats a fixed window. Release stops repetition unless Hold is enabled. Live-roll division changes during a held capture still need implementation. |
| Pitch / X-Pad level | Change sample pitch and sampler gain. During live-input roll, X-Pad level blends between the live input and captured loop. |
| Overdub | Record a four-beat pattern starting at the first hit. Turning Overdub off stops and deletes the pattern. Shift-click clears it while staying armed. |
| Hold | Latch rolls. Turn off to stop the held roll. Shift-click mutes/unmutes sampler output. |
| Default / User | Select factory advanced settings or the saved custom settings. Applying the settings editor selects User. |
| Release FX switch | Cycle Back Spin, Echo, and Vinyl Brake. |
| Release lever | Drag downward and hold, then release to return to dry audio and reset performance effects. Lever amount changes effect intensity. User settings can retain Scene, Isolate and X-Pad sections individually after release. |

The native app's File menu provides presets, WAV import, sample trim/reverse/normalization and BPM/loop mode, engine settings, and Audio & MIDI setup. `Cmd+,` opens audio setup, Space toggles bypass, and Escape resets effects. Plugin settings, import, presets, and exact parameter values are available from the context menu.

Internal drums are stored separately from the four sample banks. Imports and sample edits select bank playback; **Sample source** in settings can also select either source. Queued pad hits and recorded overdubs retain their source/bank when the current selection changes. These internal drums are synthesized substitutes; the original factory recordings are not included.

Only slot 1 (the Kick position) of each bank can loop. Set the sample's original BPM between 70 and 200 in **File → Edit selected sample**; the plugin context menu offers **Selected sample playback**. Press its pad once to start, again to stop, and again to restart. Overdub records start and stop events; strip repeats restart the same loop voice. Its speed follows performance BPM and Pitch through resampling; original-unit time-stretch, voice limits and choking remain unverified. Sample playback metadata applies in both Default and User. Legacy presets without a sample-source field retain bank playback.

Each bank holds at most 16 seconds across its four slots. Imports and preset loads reject overflow before installing assets. A new import starts in One-shot mode at 120 BPM; set its original BPM before enabling Loop. Metadata is stored in the preset/session, separately from the WAV.

Sample edits/imports and preset loads briefly suspend native audio to install assets safely. The plugin installs immutable sample banks at block boundaries. Presets reference sample files: keep those files available when moving presets to another computer.

MIDI input defaults to Off. Select a separate controller, then right-click a native knob and choose **Learn next MIDI CC**. Move through the current value for soft takeover. Notes 36–39 trigger the four pads. MIDI feedback defaults to disabled. With Auto enabled, a connected DAW's tempo takes priority over MIDI clock or input analysis in the plug-in. Switching Auto off uses the stored manual BPM.

The physical prototype's shared decoder supports Bank+pad bank selection; repeating the selected bank chord returns to internal drums and plays that pad. Hold+pad selects silently when Overdub is off and mutes the recorded lane when on. Overdub+pad deletes a lane; Tap+Nudge enters manual tempo. These are physical button chords; the desktop exposes corresponding mouse gestures above. Card-availability feedback, exact bank LEDs/chords and voice behavior still need comparison with a reference unit. Recorded touch-strip transformations and their mute/delete chords remain outstanding. The hardware design and firmware status are in [hardware/README.md](../hardware/README.md).

User settings include per-band isolator gain limits, Add/Trans/Roll patterns, Gate/Drive depth and separate per-effect Scene choices, including four delay assignments for each tempo effect, Echo filter width and Up/Down reverb filter types. The editor scrolls through the available controls; Apply selects User. Default retains the stored choices while using default DSP values. [DSP behavior and unmeasured mappings](dsp-model.md) distinguish implemented controls from reference-matched sound.

X-Pad assignments apply to both sample repetition and new live-input captures. Eight beats at 40 BPM uses a twelve-second capture. Default keeps the previous strip divisions (1/16, 1/8, 1/4, 1/2, 3/4, 1, 2, 4); switching back to User restores its saved assignments. Existing `x_roll` preset/automation values still select the same positions; host labels now identify positions because their beat assignments can change. Roll/Slip Roll/Divide Roll, oscillator envelope choices and asymmetric pitch limits remain unfinished.
