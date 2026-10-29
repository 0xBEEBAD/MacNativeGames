# Building a game without a game folder: the dm route

This note records the route used to build a working macOS app for **Hollow
Knight** (`0100633007D48000`, Unity IL2CPP, NintendoSDK 20.5.21) from an NSP
folder, without adding a game folder to this repository.

It is a best-effort route: it reuses the dm runtime that `games/mk8d` already
ships, and the generic NSP builder that `games/mk8d/third_party/nxnative`
vendors. Nothing in `games/` is changed; the app you get is a provisional
profile build (the builder itself warns "may not boot"). For Hollow Knight it
does boot and runs at 60 fps on an M4 — see [Limitations](#limitations).

## How it works

- `games/mk8d/runtime` is the dm runtime: a host-side loader that runs the
  game's own AArch64 code, with NVN mapped onto Metal. It is not tied to Mario
  Kart 8 Deluxe; the title comes from the profile.
- `games/mk8d/third_party/nxnative/build_ipa_from_nsp.py` is nxnative's
  generic NSP-to-app builder. With no game folder it runs a survey
  (`profile_guess.py`) and writes a **provisional profile** for the title, then
  builds an app with it. A profile holds the module list, memory sizes, the
  shader map, the pipeline archive and the launch settings; a provisional
  profile is a guess, not a tested port.
- The app bundles the runtime, the rewritten modules, the rewritten tables, a
  3.4 GB RomFS image and the Metal pipeline archive. No game files go into this
  repository.

## Prerequisites (versions I used)

| Tool | Version / notes |
| --- | --- |
| macOS | 27.0.1 (26A434), Apple silicon (M4) |
| Xcode | 27.1 (27A9275) **with the Metal toolchain**: `xcodebuild -downloadComponent MetalToolchain` |
| Python | 3.14 (`uv python install 3.14`) with `lz4`, `capstone`, `fonttools` |
| .NET SDK | 10 (`dotnet-install.sh --channel 10.0`), for `dm/tools/nx_extract` |
| LibHac | 0.19.0 nupkg in a local NuGet feed (see `build_mk8d.py` for the SHA-256) |
| zstd | `zstd` binary (the app build extracts the RomFS image) |
| glslang | `glslangValidator` binary (NVN shader translation) |
| SPIRV-Cross | built from the pinned source revision (see `build_mk8d.py`; no prebuilt binary in the tree) |
| keys | `prod.keys` exported from a console you own |
| game files | the base NSP; an update NSP is optional but recommended |

## Staging

Put a copy of the runtime and the builder next to each other:

```
<work>/repo/
  dm/                   copy of games/mk8d/runtime (the dm runtime source)
  scripts/
    build_ipa_from_nsp.py   upstream nxnative build script
```

Before the first run:

1. Copy the prebuilt host helper: `runtime/gfx/tools/dmsh_xlate_bin` into
   `<work>/repo/dm/gfx/tools/dmsh_xlate_bin`.
2. Build SPIRV-Cross into `<work>/repo/dm/gfx/tools/spirv_cross_bin/spirv-cross`
   (the `build_mk8d.py` logic: pinned checkout, the 11 listed sources,
   `-DHAVE_SPIRV_CROSS_GIT_VERSION` with `gitversion.h`, then check
   `--revision` prints `Git commit: vulkan-sdk-1.4.363.0 ...`).
3. `nx_extract` is built on demand by the script; a local feed works, e.g.
   `dm/tools/nx_extract/NuGet.Config` with `<clear />` plus the folder that
   holds `libhac.0.19.0.nupkg`.
4. Put `zstd` and `glslangValidator` on `PATH` (or where the script looks).

> The copy of `build_ipa_from_nsp.py` inside `games/mk8d/third_party/nxnative/`
> carries MK8D customizations, including a `TARGET_TITLE` check that rejects
> every other title. For another game use the upstream script from
> `seedds/nxnative` (the imported commit is recorded in that folder's
> `import-manifest.json`), or drop that check.

## Steps

1. **Survey.** It writes `<NSP folder>/<title ID>_survey/survey.md` and extracts
   the code modules and a RomFS manifest. `--allow-damaged` lets the survey
   open a base NSP whose Code partition signature does not verify (common with
   repacked bundles; the update's partition is usually intact).

   ```
   python repo/scripts/build_ipa_from_nsp.py "<NSP folder>" \
       -k "<keys>/prod.keys" --platform mac --survey-only --allow-damaged
   ```

2. **Build the app.** The output must end in `.app`. The provisional profile
   is written to `<NSP folder>/<title ID>_build/profile/<title ID>/`.

   ```
   python repo/scripts/build_ipa_from_nsp.py "<NSP folder>" \
       -k "<keys>/prod.keys" --platform mac-app \
       -o "<out>/<name>.app" --allow-damaged
   ```

3. **Run it.** The front end starts the bundled `dmhost` and sets
   `DM_NVN_SHMAP` to the app's own table, so double-clicking is enough. To run
   the host by hand (bring-up):

   ```
   cd <work>
   DM_ROMFS=<build>/extract/v1/RomFS.img \
   DM_SAVE=<runtime save dir> DM_TEMP=<runtime temp dir> DM_MSL_DIR=<msl dir> \
   DM_NVN_SHMAP=<build>/profile/<title ID>/shader_map.tsv \
   <repo>/dm/host/dmhost <build>/patched_v1
   ```

   The modules the host loads are the **rewritten** ones (`*.patched.bin` and
   their `*.fixups.tsv`), not the raw ExeFS modules.

## Common failures

- `ResultFsNonRealDataVerificationFailed` / `ResultFsPartitionSignatureVerificationFailed`
  on the *base-only* ExeFS read: the base NSP's Code partition does not verify.
  Pass `--allow-damaged`. If the build ID lookup aborts because a base-only
  module cannot be opened, the staging copy of `dm/games/game.py` can skip that
  module (wrap the `same_build()` failure in a warning + `continue`) instead of
  failing the whole run; the update's module still gives the build IDs.
- `tools not found: zstd / glslangValidator`: install both and put them on
  `PATH`.
- `spirv-cross is missing or not executable`: the binary must be at
  `<...>/spirv_cross_bin/spirv-cross` (a directory holding the binary).
- `the Mac app (-o / OUT_IPA) must end in .app`: pass an output path ending in
  `.app`.
- `FATAL cannot read the shader map` when running `dmhost` by hand: set
  `DM_NVN_SHMAP` to the profile's `shader_map.tsv`; the app sets it itself.

## Limitations

- The profile is provisional: memory sizes are guessed from the survey, and
  shaders that are missing from the archive are reported as
  `[nvn-mtl] shader ... is not in the shader map` and skipped.
- Verified to boot, render and run at 60 fps (Hollow Knight, `1.5.12620`
  update on `1.5.12183` base, 3300+ frames, 0 crashes); a full play-through is
  not tested.
- The app is ad-hoc signed (no notarization); the first launch needs
  right-click → Open unless Gatekeeper is relaxed.
- Save data: `~/Library/Application Support/nxnative/<title ID>/`;
  logs: `~/Library/Logs/nxnative/<title ID>.log`.
- Keep the build folder: it holds the rewritten modules, the shader map, the
  pipeline archive and the RomFS image; rebuilding rebuilds it from the NSPs.
