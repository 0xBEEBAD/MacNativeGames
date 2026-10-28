# feat(totk/audio): add 5.1 surround sound support with automatic hardware detection and stereo fallback

## Summary

This PR adds native 5.1 surround sound support to Tears of the Kingdom (`games/totk/`), eliminating the forced downmix to stereo on multi-channel audio setups (HDMI AV receivers, multi-channel USB audio interfaces, virtual surround routing) while preserving seamless automatic fallback to stereo on standard hardware (built-in MacBook speakers, headphones).

---

## Motivation

Previously, `audio_mixer.c` unconditionally downmixed all audio from the guest device sink into 2-channel stereo Linear PCM. Even though the Switch engine renders 6 discrete channels (`FL, FR, Center, LFE, Surround Left, Surround Right`), the mixer applied a fixed downmix formula and completely discarded the LFE (subwoofer) channel.

However, in low-level CoreAudio (`kAudioUnitSubType_DefaultOutput` / AUHAL), requesting 6 channels on hardware that only supports 2 channels causes `AudioUnitSetProperty` or `AudioUnitInitialize` to fail with `kAudioUnitErr_FormatNotSupported` (-10868), leading to complete silence.

This PR solves both issues by detecting hardware channel capabilities dynamically, configuring the proper CoreAudio channel layout, and implementing a resilient fallback to software ITU downmixing when needed.

---

## Detailed Changes

### 1. `games/totk/runtime/audio_mixer.c`

* **Hardware Channel Detection (`detect_output_channels`, `detect_system_channels`)**:
  * Queries `kAudioUnitProperty_StreamFormat` on `kAudioUnitScope_Output` (Bus 0) of the output AudioUnit to read the device's native channel count.
  * If the device supports $\ge 6$ channels, 5.1 mode is selected; otherwise, stereo is used.
  * Supports manual override via the `TOTK_AUDIO_CHANNELS` environment variable (`6` for 5.1, `2` for stereo).

* **CoreAudio 5.1 Initialization with Proper Channel Layout (`output_open`)**:
  * Configures `AudioStreamBasicDescription` with 6 Float32 channels (24 bytes per packet/frame).
  * Sets `kAudioUnitProperty_AudioChannelLayout` to `kAudioChannelLayoutTag_AudioUnit_5_1` (`L - R - C - LFE - Ls - Rs`), matching the Nintendo Switch Audren channel ordering.
  * **Safe Stereo Fallback**: If 6-channel initialization fails on the audio device for any reason, `output_open` catches the error, reconfigures the unit to 2-channel stereo, and logs a fallback message, preventing audio loss.

* **Discrete 5.1 vs. ITU Downmix Rendering (`audio_mixer_render`)**:
  * **In 5.1 mode (`m->channels == 6`)**: Transmits all 6 discrete channels directly to the output scratch buffer. Subwoofer (`LFE`), Center dialog, and Surround channels are preserved with full spatial separation and zero downmix loss.
  * **In Stereo mode (`m->channels == 2`)**: Retains the software downmix matrix (using the game's downmix parameters or ITU BS.775 coefficients).

* **Dynamic Ring Buffer and AudioUnit Render Callback**:
  * Expanded `ring` buffer capacity to `RING_FRAMES * 6` and `output_scratch` to `MAX_FRAME * 6`.
  * `output_push` and the CoreAudio render callback `pull()` dynamically process $N$ channels (`m->channels`), supporting 2 or 6 channels without performance overhead.
  * Diagnostic capture worker (`capture_write`, `capture_copy`) adapted to capture either 2 or 6 channels based on the active mode.

* **Switch IPC Reporting (`audio_device_handler`)**:
  * `IAudioDevice::GetActiveChannelCount` (command 5) dynamically returns the active channel count (`6` or `2`) instead of hardcoded `2`, informing the guest audio engine of the active device configuration.

* **Helper Functions**:
  * Added `audio_mixer_channels()` to query the active channel count.
  * Updated `audio_mixer_read()` to return $N$ channels of mixed frames.

### 2. `games/totk/runtime/audio_mixer.h`

* Declared `audio_mixer_read` and `audio_mixer_channels`.

### 3. `games/totk/runtime/audio_renderer.c`

* Updated `runtime_audio_probe` to explicitly set `TOTK_AUDIO_CHANNELS=2`, ensuring deterministic behavior during internal renderer tests.

### 4. `games/totk/tests/audio_routing/probe.c`

* Added `run_case_51()` to unit test the 5.1 rendering pipeline:
  * Routes discrete voice samples to Center, LFE, and Surround Left.
  * Verifies that all 6 discrete channels are preserved in the mixed output buffer without downmixing and that LFE is preserved.

---

## Platform Scope: iOS / iPadOS Unchanged

The codebase supports both macOS and iOS/iPadOS (`TARGET_OS_IPHONE`):
* On iOS, the CoreAudio subsystem uses `kAudioUnitSubType_RemoteIO` rather than macOS's `kAudioUnitSubType_DefaultOutput` (which is unavailable on iOS), and the audio session is managed externally via `AVAudioSession`.
* Therefore, the hardware channel detection routines (`detect_output_channels` and `detect_system_channels`) are guarded with `#if !TARGET_OS_IPHONE` and return `2` on iOS.
* **No changes are made to iOS / iPadOS behavior**: the iPhone and iPad targets continue to run in stereo exactly as before.

---

## Verification

* **Automated Unit Tests**:
  * `audio_routing` probe passed: all 4 stereo routing graphs + the new 5.1 surround routing graph (`run_case_51`) pass.
  * `mixer_probe` passed: verified ring buffer operations, prefill/underrun accounting, rapid pause/resume, and diagnostic capture across 7,000+ checks.
  * `test_audio_ramp` passed.
* **Compatibility**:
  * Tested stereo fallback behavior to ensure zero regressions on standard stereo outputs.
