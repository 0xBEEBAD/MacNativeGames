Suggested title: `feat: add experimental native macOS support for Age of Calamity`

Adds an experimental native macOS target for Hyrule Warriors: Age of Calamity
1.3.0 (v327680). The original ARM64 modules are rewritten ahead of time and run
directly on Apple silicon. The runtime supplies host services and maps NVN
rendering to Metal.
Original 30 fps remains the default. This draft requests review of the initial
port; full-game compatibility has not been established.

### Changes

- Add an isolated build from verified, unmodified, already merged extracted
  inputs, with copy/license provenance, offline Metal shader compilation and
  a self-contained signed app. Saves, preferences and logs live outside the app.
- Correct geometry shader bindings and reject incomplete shader packaging.
- Add keyboard/controller settings, English native UI and shortcut hints.
- Add opt-in 60 fps with Dynamic Step, plus FPS, frame-time percentiles,
  a frame-time graph, GPU timing and shader/pipeline statistics.
  Stats collection and the frame graph default off; saved choices and explicit
  environment overrides can enable them.
- Disable incomplete 120 fps support; legacy settings fall back to 60.
- Execute synthetic timing regressions directly on Apple silicon using a
  statically linked native probe, without a CPU emulator or game content.

### Validation

- **macOS / Apple M5, game 1.3.0:** built and verified the signed app; played the first
  mission with audio, keyboard and DualSense input. Smooth 60 fps gameplay was
  observed, but the Impa tower cutscene has the timing failure below. The
  compliance changes were build/probe tested, without another playthrough.
- **Root suite:** 460 tests run, one optional system-trace test skipped, no
  failures (`python -m unittest discover -s tests -v`).
- **AoC suite:** 40 tests passed, including eight native timing cases and the
  stats/control probe. Settings passed 71 checks under each of the English and
  Chinese game-language overrides; the native UI remains English.
- **Metal probes:** 221 checks passed with Metal validation enabled (vertex
  buffers, geometry, integer vertex inputs and texture-buffer fetch).
- **iOS/iPadOS:** no full app build or device test. Stats/timing C and NVN C/
  Objective-C sources compile-check against the iPhoneOS 27 SDK for ARM64,
  targeting iOS 26. The target lacks UIKit app sources and an iOS project
  template, so these checks do not establish a linked or playable iOS app.

### Known limitations

- The Impa tower cutscene has accelerated animation/camera playback at 60 fps
  while audio remains normal, including with Dynamic Step. Automatic cutscene
  fallback is not implemented or validated.
- Original 30 remains the default; 60 is experimental and 120 is unsupported.
- Later missions, complete rendering acceptance and save/reload acceptance
  remain incomplete. No iOS compatibility is claimed.

