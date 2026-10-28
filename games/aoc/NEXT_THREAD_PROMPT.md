# Next-thread prompt: implement Age of Calamity for native macOS

**Implementation has started.** For the current state and running offline build,
read [IMPLEMENTATION_CHECKPOINT.md](IMPLEMENTATION_CHECKPOINT.md),
[VALIDATION.md](VALIDATION.md) and [README.md](README.md) first. The original brief
below is retained as historical guidance; its statements that inputs and an
implementation are absent no longer describe this checkout. Extracted-directory
inputs are supported directly, without keys or NSP/XCI files.

Implement an isolated native Apple silicon macOS port of **Hyrule Warriors: Age of Calamity**, starting from the completed repository analysis in `games/aoc/ANALYSIS.md`. Read that file and `CONTRIBUTING.md` first, inspect current Git status, and preserve unrelated user changes.

The chosen foundation is **`games/jamboree`'s pinned nxnative runtime and isolated Mac build/package approach**. This decision is based on existing Age of Calamity code paths, not a similarity between the games. Do not start from TOTK/BotW, Bayonetta or Odyssey instead without concrete new evidence that invalidates this choice. At the end of the analysis, `games/aoc` contains only these planning documents; no target implementation or original-input pins exist yet.

## Objective and inputs

Produce a repeatable original-input-to-app build and a native Mac app that reaches an actual playable battle with correct rendering, sound, keyboard/controller input, and save/reload. Continue through the authorized work, diagnose concrete failures, and keep a dated validation record. If original inputs or an external prerequisite are unavailable, finish independent source/tooling work and state the exact blocked acceptance gate; do not fabricate validation.

Target the existing upstream **1.3.0 / v327680** profile first:

- Base title: `01002B00111A2000`.
- Update title: `01002B00111A2800`.
- Engine: KTGL on NVN; SDK 9.6.0.
- Expected main/submodules: `main subsdk0 sdk`, confirmed against the user's extraction.

The previous thread was not given the user's game, update, key-file, firmware or work-directory locations. Use paths already provided in this thread/context if available. Otherwise ask concisely for those input locations while continuing work that does not require them. Use only the user's owned dumps. Never request key contents in chat, print keys, alter the original containers, or commit game-derived bytes, shaders/libraries, saves or screenshots. Use the available secure secret flow if an actual secret must be supplied.

## Fixed source and provenance

The analyzed MacNativeGames commit is `8c9c71b9503f9b7d9643a4f45aa8fbcb1aff1f02`. Inspect subsequent changes if HEAD differs.

Jamboree imports nxnative **`7861e7c1a9913e020600b1cc7f65132427e9cc50`**. Read its `third_party/COPIES.md`, import manifest and licenses. Copy the necessary runtime, graphics, tools, dependencies, translator payload, Mac wrapper and tests into `games/aoc`, preserving provenance. All build/import/runtime dependencies must reside in the new game folder. No runtime or build-time reads through `../jamboree`, `../totk`, `../by3`, or another game's folder.

Retrieve the missing target profile and asserted patch source from that exact revision:

- https://github.com/seedds/nxnative/blob/7861e7c1a9913e020600b1cc7f65132427e9cc50/dm/games/01002B00111A2000/game.tsv
- https://github.com/seedds/nxnative/blob/7861e7c1a9913e020600b1cc7f65132427e9cc50/dm/games/01002B00111A2000/patches.py

Keep the MIT notice and record exact source paths/commit. Avoid importing a moving upstream runtime or an entire multi-game repository. Read the pinned development notes only as needed for a concrete target gap.

## First implementation pass

1. **Preflight the environment.** Check arm64/macOS, selected Xcode/SDK, Metal compiler, Python dependencies, .NET 10 SDK/runtime, `spirv-cross`, and the explicit local LibHac package required by the copied builder. The analysis Mac had working Metal tooling but only .NET SDK 7.0.201 and no `spirv-cross` on PATH. LibHac 0.19.0 is pinned by the existing wrapper to SHA-256 `1431267861db5ff68216315b164f10c0edab4df162cedf5429bf8a143b76de19`. Preserve local-only dependency restore; do not silently download an unverified replacement or rely on an unrelated global package cache.
2. **Create `scripts/build_aoc.py` and an independent target profile.** Adapt both the outer Jamboree wrapper and its vendored builder. Both contain Jamboree-only title/version gates. Replace manifests, module/version paths, package arguments, app/executable/bundle names, data/log folders and tests. Remove the Jamboree profile, its main allocator cut and its movie-continuation build exception from this target copy. Keep generic renderer corrections. Do not modify the donor games or the root build/update scripts.
3. **Survey and verify original inputs before accepting them.** Read content metadata, base/update composition, module build IDs, NPDM, SDK imports, NVN requirements and resource formats. Verify extraction/integrity and record full input/output hashes and tool/rule fingerprints using the copied mechanisms. Produce `assets/expected-1.3.0.json` from actual verified originals; do not copy donor hashes. Unsupported title/version/build must stop before rewrite/package.
4. **Verify profile assumptions.** Upstream build-ID prefixes are `main=c3cf52bf2b05d7310884971b50bcccb8`, `subsdk0=3ab92c3444d4ece2f52417b5d8ee86eb`, `sdk=95832210b36121e88b4f9b7b66239dad`. Compare locally; these prefixes do not replace SHA-256 integrity pins. The profile provides `mem_used=0x4800000`, `tex_flush_upload=on`, `vconv_range=on` and a full pad layout. Measure actual mapped modules and memory partition rather than enlarging the app pool to suppress failures.
5. **Set `sys_resource` explicitly from NPDM.** The pinned profile's comments describe zero but omit the row. The local generator defaults an absent row to 32 MiB; Jamboree's profile uses 16 MiB. If the target's NPDM confirms zero, set zero. This affects the SDK's allocator path and is not cosmetic metadata.
6. **Build from original modules with this rewriter.** Inspect all asserted patches and generated tables. Do not mix d2r's `DM_RULESET`/`DM_PRIVATE_GATES`, structural checker, gate layout or runtime metadata into the nxnative pipeline. Keep original ARM64 execution with no CPU interpreter, JIT or runtime CPU translation. Investigate native loader/import/TLS/thread errors in the host layer.
7. **Bring up incrementally.** Native loader and constructors → original `nnMain` → first meaningful title/movie → new game → active battle → sound/input → save and fresh-process reload. Capture the first unexplained service, ABI or rendering failure, identify its real caller/producer, fix the platform behavior and repeat. Use bounded diagnostic runs and one game/GPU probe at a time. Do not terminate an existing user game to make room.

## Keep these target-relevant mechanisms together

The copied Jamboree runtime already has the following; retain and verify them before writing substitutes:

- `runtime/gfx/tools/shader_split.py`: KTGL RDB/IDRK chunked-zlib extraction, G2S and `_DOK` shader containers, shaders embedded in main, short control sections and headerless compute.
- `dmsh_vin.py` and `nvn_mtl.m`: shadow vertex inputs and bounded CPU fallback for mixed Half2/Short2/integer fetches.
- `tbuf_as_2d` plus the matching translator: wrapped texture-buffer reads for lighting/decal lists.
- Texture-serial view reuse with proper lifetime invalidation; GPU indirect argument conversion and effects; large c1 reflection storage.
- Shared compute/copy encoder dispatches with dependency barriers. `DM_NVN_PASSGPU` and `DM_NVN_DISPATCH_OWN=1` change this behavior; do not leave them enabled in ordinary performance runs.
- Class-based HardwareOpusMultiStreamDecoder replacement and the SDK's in-process CPU audio renderer. Do not copy the other family's custom mixer or Unicorn's different C-interface ABI wholesale.
- Generic execution of rasterizer-discard vertex side effects even when transform feedback is off.

The pinned target audio patch shifts 4 MiB between sound subheaps with unchanged total. Its exact hardware/work-buffer cause remains unresolved. Verify its original instructions, document it as a compatibility workaround, and investigate the need; do not describe it as a proven general platform correction.

## Fix the shader build before calling the app efficient

Jamboree's wrapper **and launcher** force `DM_METAL_RUNTIME=1`. `dmsh_build.py` then writes a `RUNTIME_METAL` placeholder into `.metallib` files, and the host compiles adjacent MSL on first use. This path is useful for bring-up but is not the desired final default.

- Build real offline Metal libraries with matching math/invariance options and fingerprints; remove the launch-time forcing too. Invalidate/rebuild placeholder-based cache entries. Packaging should reject placeholders for the normal offline mode. A `.metallib` extension alone proves nothing.
- Generate the target's shader map/facts/pairs from the user's originals with the copied fork's **four-column package/index/stage/key format**. Do not blindly import upstream maps with an original-resource column or any donor shader/pipeline list.
- Generate fresh chain/input-stamped `c1_full.tsv` and `cb_extent.tsv` privately. Preserve the pinned translator/host contract, exact translator file-set checks, and tool/profile identity checks. `own_compilers.py` can tolerate a local compiler change without changing the shared chain; include actual compiler identity in target cache fingerprints and prove a clean rebuild. Update locks only for actual tool changes and rebuild affected outputs.
- Scan every relevant KTGL source including `_DOK` and main. Check runtime-used keys against extracted/translated keys. Classify empty slots, parse failures, untranslated stages and pipeline failures separately; do not invent shader-count thresholds or call skipped effects correct.
- Prewarm a measured title/first-battle set; lazy-load remaining compiled libraries. Treat MSL translation, Metal library compilation and GPU pipeline creation as separate costs. Adapt pipeline archives or further warm-up changes only after measuring misses in this runtime.

## Baseline behavior and enhancements

First validate the original 30 fps simulation setting with `fps_target=0`. Inspect the upstream frame stubs' off path too; zero is not proof that no generated patch executes. Then offer a tested optional 60 fps path using the coordinated task-clock, battle-step and device/event logic. Verify timed movement, attacks/animation, mission/event timers, movies and audio against wall time. A faster present interval alone is wrong.

Preserve picture quality and original game state. Do not force progression, suppress geometry, skip producer work, disable depth/effects, or enlarge arbitrary heaps to hide a defect. Frame generation, 120 fps, widescreen, render-resolution patches, mobile ports, DLC and split-screen co-op are later independent work. A presentation cap is not a higher internal render resolution.

## Tests and acceptance evidence

Run adapted packaging/profile/identity/shader-map tests, then focused native probes. Existing Jamboree tests passed during the analysis: 12 packaging/input/tool tests, 4 shader tests; Metal validation probes `t_vbuf` 43 checks, `t_geometry` 127, `t_vin` 14, `t_tbuf2d` 37. Rebuild/run these from the new target's copies in an external work directory. Add meaningful negative controls for title/build mismatch, changed original patch bytes, wrong shader stamps, placeholder libraries and unsupported inputs.

The root baseline is **not green** on the analysis Mac: 460 Python tests ran, one skipped, and `test_settings_panel` failed in eight subcases with `window 1511x850, expected height 851 at 16:9`. No import errors remained after installing dependencies. Six CI C/UBSan probes passed separately. Preserve/report that unrelated baseline; do not claim all tests pass or change unrelated settings code to satisfy this port.

For gameplay use a disposable profile, protect the user's existing saves, and document exact source commit/diff, runtime hash, input version/hash, shader chain/options, hardware/OS and settings. Verify title/movie natural end and skip, active combat with soldiers/lighting/decals/effects, menus, keyboard and a physical controller, continuous audio, actual save, full process exit, and new-process load.

Measure cold and warm startup plus first battle separately. Report complete frame-time p50/p95/p99/max and over-budget fraction, present cadence, CPU/GPU work, compile/PSO activity, dropped/error draws, footprint/Metal memory and thermal state. Keep the binary, route, save/cache and rendering settings fixed across comparisons. Heavy diagnostics and compilation must not overlap benchmark windows. No FPS promise based on a menu or another game's Mac.

Package a self-contained signed arm64 Mac app via a temporary output and atomic publication, preserve the previous working app, keep saves/logs/writable caches outside signed resources, and verify signatures again after play. Use a clear target-specific Application Support folder and session logs. Do not bundle .NET/LibHac/shader-translation build tooling into the runtime app.

Deliver source changes confined to `games/aoc` (plus a single root README game-list entry only when an honestly described runnable port exists), build/run instructions, provenance/notices, a dated `VALIDATION.md`, and the achieved milestone with precise remaining blockers. Distinguish newly tested results from inherited historical claims. Continue until the usable Mac milestone is complete or a concrete missing input/external condition prevents further meaningful work.
