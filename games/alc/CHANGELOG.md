# Astral Chain port: work log

A record of how this port is being made, for anyone who continues it or tries the same with another game. Each entry
says what was found, what was done and why, what went wrong on the way, and how it was checked. Newest entries go at
the bottom of [Log](#log); [Status](#status) is kept current. The plan this work follows: [PORTING-PLAN.md](PORTING-PLAN.md).

Conventions: dates are absolute; "verified" means a check with a recorded result, never "it looked right". Game data,
keys and saves are never committed (see `.gitignore`).

## Status

| Stage | Goal | State |
|---|---|---|
| 0 | Feasibility: does the game fit the by3 architecture? Code and data out of the dump, verified | done 2026-10-29 |
| 1 | Code rewritten for Apple silicon; merged RomFS | done 2026-10-29 |
| 2 | A runtime fork that boots to `nnMain` | |
| 3 | Follow every unknown service / command / NVN call until the first `nvnQueuePresentTexture` | |
| 4 | Playable: picture, audio (Wwise), input, saves; 30/60 fps and resolution patches | |
| 5 | TotK-grade polish: app, presets, shader seed, shared shader list, MetalFX | |

## Log

### 2026-10-29: stage 0, feasibility

Inputs: one 9.8 GB XCI (`异界锁链-v1.0.1-….xci`, card image) holding **base and update Program NCAs** —
base `6db3410b….nca` 10.34 GB (title `01007300020FA000`, code 1.0.0, cnmt version 0) and update `31735cd4….nca`
195.8 MB (base title ID retained, Meta `01007300020FA800`, cnmt version 65536 = **1.0.1**, the game's final version).
`prod.keys` from the same Switch. A community cheat file for 1.0.1 sits next to the dump; its folder name is the
build ID prefix it was made for, which is how the build ID below is cross-checked.

Findings, each read from the dump:

- **The update code is retail 1.0.1.** main's build ID is `4B159F0F7A360669738390EE8657B4F…`, matching the cheat
  folder prefix; the base NCA's main is 1.0.0 (`ED2026B20685971F8…`). The build uses the update's code, as with by3.
- **Two modules, not three**: the ExeFS is `main`, `sdk`, `rtld`, `main.npdm` — **no `subsdk0`** (by3 and TotK have
  three). The loader, Makefile and prepare scripts must handle a two-module set. main is 7.7 MB NSO,
  214.9 MB decompressed (by3's main is smaller); sdk is 5.2 MB NSO, 13.1 MB decompressed. Every ExeFS block hash
  verified for both.
- **43 services in the npdm** and no NPLN/gRPC/OpenSSL stack — this 2019 game predates it, so the online stubbing
  by3 needed (`nifm`, sockets, `ssl`, `friends`, `bcat` plus NPLN's own services) collapses to the plain offline set.
  Notable allows: `nvdrv`/`vi:u` (NVN), `audren:u`/`audout:u`/`audin:u` (audio), `hwopus` (Opus decode),
  `pl:u` (shared fonts), `ldr:ro`, `aoc:u` (DLC), `acc:u0`, `mii:u`, `irs`, `nfp:user`, `caps:su`/`caps:u`.
- **NVN surface ≈ by3's.** main imports 513 `nvn*` names; 512 are in by3's 523-name table, the one gap is
  `nvnBootstrapLoader` (older SDKs fetch the function table through it — needs one host entry in the loader/thunks).
  The middleware version string in sdk reads `1.2.11.f-NINTENDO-SDK-v1`; the SDK release number is not exposed as a
  plain string and will be read from `nvnDeviceGetInteger` at boot.
- **Middleware survey** (strings of decompressed main):
  - Audio is **Wwise** (`sound/WwiseInfo.wai`, `.bnk` ×33, `.wem` ×8172 in the RomFS, `AK::OpusDecodingThread`
    decoding through `nn::codec::HardwareOpusDecoder` / `hwopus`) — the same shape by3 already plays through
    `audout:u` with `runtime/audio_out.c`.
  - Data is **Platinum `.pkz` archives** (82 files, 7.58 GB) — by3's game lists `Contents:/` to find them;
    `movie/ev%04x.avi`-style strings exist but…
  - …the actual movies are **`.bk2` (Bink Video 2), 412 files, 1.85 GB** — the one genuinely new middleware.
    TotK's movie host decodes VP9 WebM; Bink 2 needs its own decoder. Plan: stub the movie host first (complete
    playback events without frames) so nothing hangs, real decoder as a later stage-4/5 item.
- **RomFS.** The base section verified through all six IVFC levels: 8,701 files, 10,309,560,892 bytes,
  SHA-256 `cdfb7043…`. The update NCA carries a 182.8 MB BKTR patch section (IVFC superblock, AES-CTR-Ex) whose
  indirect table points into the base section or the update data — by3's `merge_romfs.py` layers, minus the sparse
  layer (this base is complete, being a card image). Stage 1 adapts it: base `romfs.bin` is already decrypted and
  verified, so the merge reads the update's indirect + AesCtrEx tables and applies them over the base image, then
  verifies the merged image through the update section's own six IVFC levels.

Tooling brought into this folder (see `third_party/COPIES.md`): `extract_exefs.py` (by3) and `extract_romfs.py`
(totk), both changed to take `--title` / `--update-title` instead of hardcoded Tears of the Kingdom IDs; with a card
image holding both Program NCAs, `program_nca` now picks the update NCA by its BKTR section marker and accepts the
update's Meta NCA in the base branch. Pitfall found on the way: by3's `extract_exefs.py` was an un-adapted TotK copy
(by3's own tool is `extract_code.py`); the TotK title-ID error is how this surfaced.

Verified:

- ExeFS (update, and base for the record): FS header, hash table and every block verified (`extraction-manifest.json`
  in `AC_build/extracted/v10{0,1}/`).
- Base RomFS: all six IVFC levels, 629,246 data blocks at level 5; one flipped byte would fail a block.
- `assets/expected-v1.0.1.json` pins: title/update title IDs, cnmt versions, main build ID, both Program NCA
  identities, the update ExeFS hashes, and the base RomFS size/SHA-256/file count. The merged-RomFS and
  rewritten-module hashes are stage 1's additions.

Open questions carried forward:

- SDK/NVN version numbers (read at boot; shader GPU-code version expected ≤ the layer's table range, older is safer).
- npdm's application pool and heap figures (by3 learned its pool at `svcGetInfo`; same expected here) — stage 2.
- Whether `nvnBootstrapLoader` needs a real implementation or the game's nvdrv client never calls it when all names
  resolve — stage 2/3.
- Bink 2 strategy: stub first, decoder later (stage 4).
- `ldr:ro`, `htc`/`htcs`, `banana`/`o6j`/`pcm`/`s2g`/`ntc`/`bsdcfg` in the service list: probably allowed but
  unused; the host fails loudly if one is really called.

### 2026-10-29: stage 1, the code rewritten for Apple silicon; the merged RomFS

**The patch area had to move below the module base.** main decompresses to 214.9 MB, 191 MB of them zero-filled
BSS (the engine's static arenas; the guest reaches them through adrp pairs the rewrite does not touch, so BSS
cannot move). The rewriter appends the patch area after the image, which put it ~200 MB from the first text
sites — beyond a B/BL's ±128 MB reach. sdk was never a problem (13 MB image). The d2r copy in
`third_party/d2r` now writes the patch to its own file `<name>.patcharea.bin` and records a signed `PATCH_OFF`
plus `PATCH_SIZE`/`ARENA` in `fixups.tsv`: images over 96 MB take a 32 MB arena below the module base
(PATCH_OFF −0x2000000, every site within ~42 MB), small images keep the patch appended exactly as before
(sdk's flat view is byte-for-byte the old one-file layout). The runtime loader maps the two parts at their
true addresses — stage 2's `map_module` change.

**Rewrite results** (`DM_RULESET=native DM_PRIVATE_GATES=0`): sdk 10,957 sites (patch 440,628 bytes), main
5,426 sites (patch 219,824 bytes). main needed two rewriter extensions:

- `ldrsw_table` (the BotW-1.6.0 jump-table shape) did not match Astral's variant at `main+0x6db4a0`: the
  `ldrsw` writes the index register itself (E == I, perfectly fine — the index is dead after the load), and
  the table base (`adrp x24, #0xbec000; add x24, x24, #0x944`) sits at the function's entry
  (`0x6dad60`), ~1,800 instructions from the dispatch, not in the 48-instruction window. The scanner now
  accepts both: after the load only the table base must survive, and the base pair is searched from the
  function start. Five such tables matched; every entry target is checked to be an instruction of its
  function, as before. (Table at `0xbec944`, 6 entries, targets `0x6db4a4`–`0x6db544`.)
- One `spset` site (`mov sp, x18` — the by3-era block kind) — the earlier extension paying off.

**Verification** (all recorded):

- `structck.py`: sdk 0 violations, 11,106 trampoline exits all legal; main 0 violations, 5,543 exits all legal.
- `equiv.py` (Unicorn, random states, per site ≥2 effective trials): sdk 29,508 effective trials, 0 divergent;
  main 14,531 effective trials, 0 divergent. Negative controls: 600 mutations per module (half a trampoline
  exit retargeted +4, half the replaced instruction nopped) — all 1,200 caught.
- Two rewrites give identical bytes (`build_src.sha256` pins the rewriter).

Pitfalls of this stage, so nobody repeats them (all in the adapted checkers, each caught by a failing run):
a checker that walks the patch must convert decoded branch targets back to guest addresses (PC-relative
targets inherit the flat view's shift); patch-region membership needs the upper bound once the patch is not
the only thing above the text; capstone reports an instruction at a negative base as an unsigned 64-bit
address; and "is this branch back to text" must ask "outside the guest patch span", not "below PATCH_OFF" —
that one is inverted for the arena layout.

**Merged RomFS.** `scripts/merge_romfs.py` (adapted from by3's merger: no sparse layer — this base is
complete) applies the update's BKTR patch section (indirect table + one AES-CTR-Ex row) over the verified
base `romfs.bin` and verifies the merged image through the update section's own six IVFC levels:
629,288 blocks at level 5, 8,701 files, 10,310,254,332 bytes, SHA-256 `20904f30…`; 10,147,756,960 bytes from
the base, 182,747,996 from the update. One real find on the way: the indirect table's storage-0 targets are
base **section** virtual offsets — the base section begins with its own hash tree, so reads must subtract the
base section's level-5 offset (`0x134c000`). The first attempt (reading romfs.bin directly at the target)
failed IVFC level 5 block 9; level 4 had verified, which is what localized the defect to the base segment.

`prepare_modules.py` (by3's analysis-ELF tool, `subsdk0` skipped) inventories the two modules: main exports
24,737 symbols / imports 13; sdk and rtld recorded in `AC_build/extracted/v101/elf/`.

`assets/expected-v1.0.1.json` now pins the rewritten modules (`main.patched.bin`, both `patcharea.bin`s,
`sdk.patched.bin`) and the merged RomFS alongside the stage-0 records. The build re-checks every one of them.
