> Historical pause checkpoint, superseded by the later records in VALIDATION.md.
> The shader compiler completed and an app was packaged after this checkpoint.
> Dynamic FPS and the stats pane are now under validation; do not resume work
> using the old PIDs, shader-chain status or build instructions below.

# Resume checkpoint — 2026-10-27, 14:21 EDT

The user paused to disconnect and will resume later. **Leave the already-running
offline shader compiler alone.** No game process remains running. Do not start
a second build in the same workspace or restage its sources while it compiles.

## Current work and background build

- Source changes are confined to `games/aoc`, currently untracked. HEAD remains
  `8c9c71b9503f9b7d9643a4f45aa8fbcb1aff1f02`; no donor/root changes.
- Workspace: `/Users/jansantiago/MacNativeGames-work/aoc-1.3.0`.
- Running outer build PID 68335, vendor stage PID 68794, compiler driver PID
  68835 at checkpoint. Verify current commands before acting on any PID.
- Compiler progress: **30,503 / 40,729 keys, 75%** at 14:21:10. These are
  intermediate progress counts, not a successful final build. Last estimate
  was 17m30s remaining; compilation is not guaranteed to finish without errors.
- Progress: `WORK/build-shaders.log`; detailed compiler summary/errors:
  `WORK/build/logs/dmsh_build.log`.
- Tool exec session was 7876. The shell process is independent; ordinary `ps`
  and logs can establish completion on resume. Let completion write the full
  input stamp and c1/uniform tables. It does **not** automatically package an app.
- Whole-game libraries: `WORK/build/shader/cache/b-3d0c91995e05`.
  Profile inputs digest: `cac098007259`.
- A separate, incomplete diagnostic cache exists at `WORK/validation/shader-cache`.
  It must never substitute for the normal package's complete library set.

## Inputs and tools already verified

Original extracted root:
`/Users/jansantiago/Downloads/RYUJINX/GameRoms/_Files AOC`.
It contains ExeFS and a RomFS directory tree. Original files are preserved;
separate APFS clones are in `WORK/build/extract/v327680`.

All three game-module build IDs match 1.3.0/v327680. Full NSO/segment and NPDM
pins plus the canonical RomFS digest are in `assets/expected-1.3.0.json`.
NPDM program ID matches; system resource is zero. RomFS has 1,101 files and
11,719,163,910 bytes, excluding Finder metadata. Full private inventory:
`WORK/input-report.json`. Container integrity and base/update composition are
unavailable from these extracted files and have never been claimed.

The user supplied a prod.keys path, but it was neither needed nor read. No
NSP/XCI or LibHac is required for the implemented extracted-directory path.
The user confirms **no existing game save is available**.

Python: `/private/tmp/macnative-aoc-analysis-venv/bin/python` (3.14.7; lz4 4.4.5,
capstone 5.0.9, fonttools 4.68.0). .NET SDK 10.0.403 is privately installed under
`WORK/dependencies/dotnet`, with Microsoft's published archive SHA-512 checked.
Homebrew spirv-cross 1.4.363.0 and zstd are available. Xcode 27.0 (27A266a), SDK
27.0, Metal 32023.921, Apple M5 / 16 GiB / macOS 27.0.1.

## Newly achieved and limitations

- Isolated pinned runtime/profile, provenance, extracted-input wrapper and
  packaging implementation exist. No donor reads at build/runtime.
- Native rewrite passes all fixed-address original-instruction assertions.
  Repeating after strengthening the 12-byte frame-step assertion produced
  identical main/subsdk0/sdk images. Rewriter proof checks 19 output hashes.
- Original nnMain, constructors, native SDK audio, movies and active battle run.
- `movie-03` completed Movie001 naturally: 5,589 packets out, 5,588 pictures,
  matching the original 186.452937-second movie. `save-01` naturally completed
  that movie again and skipped Movie002 with two Plus presses separated by a
  release. Movie002 stopped after 730 pictures versus its 79.813070-second full
  duration. Captures/logs stay private.
- `battle-01` rendered Link, soldiers/Bokoblins, terrain, grass, shadows, attack
  effects and HUD; 160 KOs and the Moblin objective were observed. **The user
  confirmed DualSense movement/attacks/pause/audio work, and confirmed WASD,
  I attack and Return pause/resume work.** No need to ask those questions again.
- Physical DualSense detected as player 1. CoreHaptics helper initialization
  failed (-4810); rumble remains unverified. Button/stick input worked.
- Partial-cache runs had missing effects as new keys appeared. They are not
  final rendering-completeness or performance acceptance. No keys observed so
  far were absent from the extracted map, and no NVN unimplemented-call or PSO
  failure was found in battle-01. Partial cache lacked full uniform proof tables.
- Actual game-initiated initial save exists (`svdt`, 1 MiB, SHA-256
  `9e9a16102b28fa0bdf12a31872e8fb3d489adae6ded6b407c63ba84ff29995fb`). New processes
  reopened it successfully. **Progress save/reload has not passed**: no changed
  progress file was committed before the bounded tests ended. The first-scenario
  system menu exposed only Tutorials/Options. Continue normal gameplay to a
  genuine save point; do not call a save function directly or force progression.
- `save-02` ran 20 minutes and exited 0. Its ordinary input script reached the
  Moblin objective but spent time navigating; the mission was not cleared. Its
  initial option test changed vertical camera inversion temporarily and restored
  it before combat. The committed save hash remained unchanged.

Current compiled host includes Mac thermal/low-power diagnostics and has SHA-256
`21c5688cd174dc056ae05676f7a7ad7a186dc4178fe3c374836c32527a099b89`.
It built successfully but **has not yet been run**; the gameplay runs used the
earlier `fe6c32d...` host. Rerun native validation on the final binary.

An exploratory audio-sizing diagnostic called the unavailable hardware audren:u
path and exited 42 (`movie-02`). That probe was removed; CPU/manual sizing is
unchanged. The audio heap workaround's underlying discrepancy remains unresolved.

## Tests and next steps

Latest AoC tests: **22 passed**; shader source tests: **4 passed**. Copied host
suite exited 0. Metal validation probes: t_vbuf 43, t_geometry 127, t_vin 14,
t_tbuf2d 37 checks, all zero failures. Settings UI: 14 checks per English/Chinese,
all passed. Root suite: 460 tests, eight known 1511x850-vs-851 settings failures,
one skip; unrelated files unchanged. Logs: `WORK/tests-*.log`.

1. Read compiler completion/summary and `_b_build.json`; classify all failed,
   empty/folded/untranslated stages. Do not infer coverage from counts alone.
2. Check real MTLB libraries, matching stamps and generated c1/cbuffer tables.
   Source wrapper rejects placeholders and incomplete keys/variants. Exact
   layer-only geometry is separately classified; the two target geometry shaders
   should be inspected from their final reflection. One already compiled as
   real compute geometry plus topology variants.
3. `scripts/run_aoc.py` makes frozen binary/rewrite snapshots and disposable
   saves; `diagnostic_shaders.py` compiles only missing observed keys in a
   separate cache. `~0.3` in control.txt is a neutral release delay. Avoid blind
   movie skip scripts: first Plus reveals the prompt, another Plus skips.
4. A private prewarm seed was generated from actual title/battle records:
   223 shader rows, 290 render rows, 28 compute rows. Provenance:
   `WORK/validation/prewarm-seed.json`. Verify its cost/use on the completed
   library, then lazily load the rest. The reader's `_b` suffix bug is fixed.
5. Validate final title/movie and combat rendering without missing libraries;
   reach an actual save point, exit, copy that save and load it in a new process.
6. After compiler activity stops, measure fixed-route cold/warm windows with
   final sources/binary/cache/save. `analyze_run.py` reports complete percentile
   statistics without adding overlapping costs. `DM_MEMSTAT` now records Mac
   thermal/low-power values alongside footprint/Metal memory.
7. Package the final self-contained signed arm64 app to a **new** output path,
   test its launch and signatures after play. No app has been packaged yet.
   Normal command is documented in README; use `--phase package` only after
   current outputs pass. App publication is atomic and excludes replacement;
   writable state is outside signed resources. Runtime dependencies are system
   frameworks only. Update VALIDATION.md with exact final results and gaps.

Do not claim the task is finished. The user requested a pause, not cancellation.
