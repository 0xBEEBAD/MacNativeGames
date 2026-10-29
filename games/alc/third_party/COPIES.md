# Where each copied file came from (folder and commit), per CONTRIBUTING.md

Copied 2026-10-29, sources at repo commit 6b0c377 (by3) and 6b0c377 (totk):

## scripts/

- `scripts/extract_exefs.py` <- `games/by3/scripts/extract_exefs.py` (XCI/NSP in-place ExeFS extraction).
  Changed since the copy: the hardcoded Tears of the Kingdom title IDs in `program_nca` are now
  `--title` / `--update-title` arguments, and with a card image holding both Program NCAs the update is
  picked by its BKTR section marker while the base branch accepts the update's Meta NCA.
- `scripts/extract_romfs.py` <- `games/totk/scripts/extract_romfs.py` (six IVFC levels, RomFS index).
  Changed since the copy: `--title` / `--update-title` arguments for the parameterized `program_nca`.
- `scripts/merge_romfs.py` <- `games/by3/scripts/merge_romfs.py` (BKTR merge, six IVFC levels, index).
  Changed since the copy: the sparse base layer is gone — this base is a complete card image, so the
  indirect table's storage-0 reads go to the already-verified base `romfs.bin`, shifted by the base
  section's own level-5 offset; both Program NCAs are selected with `extract_exefs.program_nca`.

## third_party/d2r/ (the NSO rewriter and its checkers)

Copied from `games/by3/third_party/d2r/`. Changes since the copy, all needed for Astral Chain's main
(205 MB image, 191 MB of it BSS that cannot move):

- `patch_nso.py`: the patch area lives in its own file, `<name>.patcharea.bin`, mapped at a signed
  PATCH_OFF (`fixups.tsv` now records `PATCH_SIZE` and `ARENA`). An image over 96 MB takes a 32 MB arena
  below the module base (PATCH_OFF = -0x2000000) because a B/BL reaches only +/-128 MB and a patch
  appended after this image would sit ~200 MB from the first sites. Small modules keep PATCH_OFF right
  after their image, their one-file layout byte for byte. `ldrsw_table` also learned Astral Chain's
  jump-table shape: the load may write the index register itself (E == I), and the table base
  (`adrp`/`add` pair) may sit at the function's entry, far outside the dispatch's window.
- `structck.py`: builds the old flat view ([image][pad][patch]) from the two files; every patch address
  is seen at +SHIFT; branch targets decoded inside the patch go back by SHIFT before classifying;
  `gates.tsv` keys stay guest addresses.
- `equiv.py`: same flat view; `mk()` maps the two parts at their true guest addresses; the trampoline
  head, exit-b and mutation machinery use the flat indices; text-target tests treat the patch as the
  guest span [PATCH_OFF, PATCH_OFF + PATCH_SIZE).
- `prepare_modules.py` (also copied to `scripts/`): skips a missing `subsdk0` (Astral Chain has
  main/sdk/rtld only).
