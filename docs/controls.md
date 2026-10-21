# Performance controls

The main surface follows the RMX-1000 layout. The amber and teal skin and RMX badges distinguish this project. These are original algorithms; an equivalent control layout does not establish an equivalent sound.

| Control | Software behavior |
| --- | --- |
| Input / Output level | Drag vertically; Shift makes fine changes. Double-click or right-click for an exact value. |
| Quantize | Align pad triggers to the next sixteenth note. |
| Auto | Analyze incoming audio and follow detected tempo. The button pulses while confidence is low. Detection targets 70–180 BPM; half/double-time ambiguity remains possible on music. |
| BPM display | Drag or double-click to enter manual tempo, 40–240 BPM. Switch Auto off for manual control. |
| Tap | Tap in time at least twice. Tapping disables Auto. |
| Nudge − / + | Adjust manual tempo by 0.1 BPM and disable Auto. |
| Input / X-Pad source | Independently include or exclude each source from the effects. Both may be off. |
| Isolator / Cut-Add / Trans-Roll / Gate-Drive | Select the band processing mode. Low / Mid / Hi control their respective bands. |
| Scene FX ring | Select an effect; press the selected effect again to bypass Scene FX. |
| Large Scene knob | Set effect depth. Moving it enables Scene FX. |
| Sub parameter 1 | Set the tempo division; in reverbs it changes room size. |
| Sub parameter 2 | Adjust delay feedback character or reverb damping and decay. |
| Bank | Cycle through four banks. The bank indicators above the pad buttons show the selected bank. |
| Roll | Select live-input roll instead of the sample bank. |
| Kick / Snare / Clap / Hi Hat | Trigger the selected sound; number keys 1–4 do the same. |
| X-Pad strip | Press/drag to repeat the selected sound at the touched beat division. Release stops repetition unless Hold is enabled. |
| Pitch / X-Pad level | Change sample pitch and sampler gain. |
| Overdub | Record pad events into a repeating 16-beat pattern. Shift-click clears the pattern. |
| Hold | Latch rolls. Turn off to stop the held roll. Shift-click mutes/unmutes sampler output. |
| Default / User | Select factory advanced settings or the saved custom settings. Applying the settings editor selects User. |
| Release FX switch | Cycle Back Spin, Echo, and Vinyl Brake. |
| Release lever | Drag downward and hold, then release to return to dry audio and reset performance effects. Lever amount changes effect intensity. |

The native app's File menu provides presets, WAV import, sample trim/reverse/normalization, engine settings, and Audio & MIDI setup. `Cmd+,` opens audio setup, Space toggles bypass, and Escape resets effects. Plugin settings, import, presets, and exact parameter values are available from the context menu.

Sample edits/imports and preset loads briefly suspend native audio to install assets safely. The plugin installs immutable sample banks at block boundaries. Presets reference sample files: keep those files available when moving presets to another computer.

MIDI input defaults to Off. Select a separate controller, then right-click a native knob and choose **Learn next MIDI CC**. Move through the current value for soft takeover. Notes 36–39 trigger the four pads. MIDI feedback defaults to disabled. A connected DAW's transport takes precedence over tap/automatic tempo in the plugin.
