# Hyrule Warriors: Age of Calamity — experimental native macOS target

[Source copies](third_party/COPIES.md) · [Licenses](THIRD_PARTY_NOTICES.md)

This directory contains an isolated Apple silicon target for **Hyrule Warriors:
Age of Calamity 1.3.0**, title ID `01002B00111A2000`. The original ARM64 modules
are rewritten ahead of time and execute natively; Horizon services run through
the host and NVN commands map to Metal. This is an experimental bring-up. Native
gameplay has been reached with keyboard and DualSense input and audio. Full
rendering, save/reload and packaged-app acceptance remain in progress; a
successful build is not a claim that the full game works.

The supported input is an unmodified, already merged **1.3.0 / v327680 extracted
directory**, containing `ExeFS/{rtld,main,subsdk0,sdk,main.npdm}` and a `RomFS/`
directory tree. NSP/XCI files, keys and LibHac are not needed for this mode.
Other builds and RomFS images are rejected. This path does not claim base/update
composition, NCA signature verification or container integrity verification.

The inspected input's NSO hashes/build IDs, segment hashes, NPDM and RomFS tree
digest are pinned in [expected-1.3.0.json](assets/expected-1.3.0.json). Every
build verifies the files, uses APFS clones in a separate workspace, and never
patches the originals. The tree digest is SHA-256 over sorted UTF-8 rows
`sha256<TAB>size<TAB>relative POSIX path<NEWLINE>`; Finder `.DS_Store` is
excluded. The full per-file inventory is local build data and is not included.

## Build

Use an Apple silicon Mac with macOS 26 or later, Xcode and its Metal toolchain.
Build dependencies are Python 3 with `lz4`, `capstone`, `fonttools`, and
`backports.zstd` when using Python before 3.14; .NET SDK/runtime 10; `spirv-cross`,
`zstd`, and `make`. The translator payload is pinned and verified before
staging. No build tooling is bundled in the runtime app.

```sh
python3 -m venv /path/to/aoc-python
/path/to/aoc-python/bin/pip install lz4 capstone fonttools backports.zstd
/path/to/aoc-python/bin/python games/aoc/scripts/build_aoc.py "/path/to/extracted" \
  --work-dir "/path/to/private-aoc-work" \
  --output "/path/to/Hyrule Warriors Age of Calamity.app"
```

Work and output must be outside the checkout and original input directory. Use a
new output path; an existing app is preserved. The builder supports `--phase
inspect`, `rewrite`, `host`, `shaders`, or `package`; the default `all` runs all
stages. Packaging publishes a temporary bundle only after signing and strict
verification. The app stores save data, preferences, temporary files and logs
under `~/Library/Application Support/Hyrule Warriors Age of Calamity/`.

## Controls and diagnostics

Keyboard defaults are WASD for movement, J/K/U/I for A/B/X/Y, and Return for +.
F1 or Command-comma opens settings. Supported physical controllers use
GameController.

For bounded diagnostics, `scripts/run_aoc.py --work-dir WORK --session NAME
--seconds 60 --window --audio` creates a disposable save and freezes the
executable/rewrite outputs. `--save-from` copies a prior validation save for
fresh-process reload checks. The session's `control.txt` accepts the host's
button and screenshot commands. No live user profile is changed.
`scripts/analyze_run.py SESSION --start SECONDS --end SECONDS` summarizes an
explicit timing window, including percentile statistics and overlap caveats.
The runner freezes the binary, rewritten modules and generated profile tables.
`--host-from` selects a prior binary snapshot for a recorded regression run.
For package validation, `DM_AOC_PROFILE=/existing/absolute/disposable-directory`
selects separate writable state; paths inside the signed app are rejected.

The default preserves the game's original 30 fps simulation. The inherited 60
fps mode has not passed timing acceptance and is not offered. A sound-heap
compatibility patch moves 4 MiB between subheaps without changing their total;
its underlying hardware/work-buffer discrepancy remains unresolved.

## Tests

```sh
make -C games/aoc test PYTHON=/path/to/aoc-python/bin/python
make -C games/aoc test-gpu PYTHON=/path/to/aoc-python/bin/python WORK=/path/to/private-probes
```

The tests use synthetic inputs or standalone GPU probes; they do not replace
gameplay testing. This repository contains no game files, keys, saves,
screenshots or translated game shaders/libraries.

## Layout

| Path | Purpose |
|---|---|
| `runtime/host` | Native loader, service layer and macOS input/audio front end |
| `runtime/gfx` | NVN/Metal implementation, shader tools and GPU regressions |
| `runtime/tools` | Executable inspection, rewriting and related build tools |
| `runtime/games/01002B00111A2000` | Version-gated profile and game-specific patches |
| `scripts`, `app`, `assets`, `tests` | Build pipeline, launcher, input pins and tests |
| `third_party` | Pinned upstream copies, patches and provenance |
| `prebuilt/macos-arm64` | Verified shader translator payload |

The runtime is based on pinned nxnative. See [COPIES.md](third_party/COPIES.md)
for source provenance and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for
license notices.
