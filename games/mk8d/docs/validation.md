# Validation record

Date: **2026-10-28**. Game: **Mario Kart 8 Deluxe 4.0.1**, `0100152000022000`, update `v1507328`, SDK 4.4.0. The 4.0.1 ExeFS sizes, SHA-256 values and build IDs are in [expected-4.0.1.json](../assets/expected-4.0.1.json).

Hardware: MacBook Pro (`MacBookPro18,2`), Apple M1 Max (GPU `applegpu_g13s`), 32 GB. OS: macOS **27.0.1 (26A434)**, Xcode 27.1 (Metal `32023.921`), .NET SDK 10.0.102, Python 3.14.7. This is the test machine, not a performance promise for other Macs. iOS, iPadOS and visionOS were neither built nor played for this target.

Inputs: the player's own base game NSP (1.0.0) and 4.0.1 update NSP, with their common tickets. A third NSP in the same folder, add-on content, was left out by the wrapper (`ignored (not the base game or the 4.0.1 update)`) and never reached the build.

## Checks without game data

| Check | Result | What it establishes |
|---|---|---|
| `make -C games/mk8d test` | 12 passed | Tool checksums and file set, staging (executable tools, local NuGet config, chain header), input selection by ticket (add-on content left out, other updates refused), the builder's title / add-on / version gates, the pinned-hash gate before the rewrite, offline LibHac, the pins matching the profile's build row, no RomFS path in the profile's tables |
| `make -C games/mk8d test-gpu` (Metal validation on) | `t_cube_placeholder` 42 checks, `t_vbuf` 84, `t_geometry` 1,920; 0 failed | The copied NVN layer builds from this folder and passes its regressions on an M1 Max, among them the zero cube for a 2D array in a cube slot that this game's races need |

## The port against an unmodified upstream build

To tell the port's changes from the game's behaviour on this Mac, the same two NSPs were first built with an unmodified nxnative checkout at `062cd06` (`scripts/build_ipa_from_nsp.py --platform mac-app`, outside the repository), and both builds were compared stage by stage.

| Stage | Upstream | Port | Comparison |
|---|---|---|---|
| Extraction | 6,602 files, 11.3 GB, 0:19 | the same | the same NSPs |
| Pinned 4.0.1 ExeFS | — | `main`, `main.npdm`, `rtld`, `sdk`, `subsdk0` match | |
| Rewrite | `main`, `subsdk0`, `sdk` | the same | all 18 rewritten modules and tables byte-identical; only `build_src.sha256` differs (it lists upstream's other games' `patches.py`, which the port does not carry) |
| Shader split | 29,651 shaders, 18,747 pairs | the same | `shader_map.tsv`: the same stage and key in every row, packages named by the generic group (`vs_archive.bin` 12,522 + `vs_main.bin` 8, `ps_archive.bin` 17,063 + `ps_main.bin` 29, 28 compute, 1 geometry); `shader_facts.tsv`, `shader_pairs.tsv`: identical |
| Mac shaders | 29,651 of 29,651 ready, 36:37 | | chain `a78f966a7b38` (upstream) / `fd8ba7b84f3c` (port) |
| Pipeline archive | `applegpu_g13s` (metal-tt) | | |
| App | 13.1 GB | | |

## Upstream baseline on this Mac

Runs of the upstream app with `DM_LAUNCHER=0`, a private save folder, muted Core Audio with a PCM dump (`DM_AUDIO_MUTE=1`, `DM_AUDIO_DUMP`), scripted keys (`DM_KEYS`) and screenshots (`DM_NVN_SHOT`):

- **Boot to the title** (fresh save, 75 s): "Press L+R to start" and "Ver. 4.0.1" by frame 900; 75 s of stereo audio, every sampled block non-zero (RMS 990, peak 7,563).
- **Mii pick** (fresh save, `f960:L+R~0.3,f1300:Right,f1450:A,…`): "Select a Mii" with the six default Miis (heads empty: no MiiModel firmware data, a known limit), then the single-player menu and the class choice with its movie preview; `userdata.dat` written.
- **A race** (that save, upstream's route `f960:L+R~0.3,f1260:A,…,f4300:A~70`): 50cc Grand Prix, Mushroom Cup, Mario Kart Stadium's intro and the race (lap 1/3, an item held, coins counted). On screen 299–300 of every 300 frames, 1–3 dropped, p99 16.67 ms (60 fps); footprint 2.7 GB.
- One red line per run, the same in every run: `[nvn-mtl] [RED] texture ID … not registered`.

## The port's app

To be filled in.

## Known limitations

- Mii heads draw nothing: the host ships no MiiModel firmware data (nxnative's stand-in has every part empty). Bodies and favourite colours show.
- Only 4.0.1 with no add-on content: the Booster Course Pass courses are in the update's data, but the game offers them only with the purchased add-on content, which this target does not take.
- Online play and local wireless are unavailable by design.
- One `[RED] texture ID … not registered` line per run, also upstream; its effect on the picture was not seen in the runs above.
- The app is ad-hoc signed; the first launch waits while macOS assesses the 13 GB bundle. Distribution and other Macs were not tested.

Screenshots, saves, logs and translated shaders used here are not in Git: they contain or derive from game content.
