# Where each copied file came from (folder and commit), per CONTRIBUTING.md

Copied 2026-10-29, both sources at repo commit 6b0c377:

- `scripts/extract_exefs.py` <- `games/by3/scripts/extract_exefs.py` (XCI/NSP in-place ExeFS extraction).
  Changed since the copy: the hardcoded Tears of the Kingdom title IDs in `program_nca` are now
  `--title` / `--update-title` arguments; otherwise unchanged.
- `scripts/extract_romfs.py` <- `games/totk/scripts/extract_romfs.py` (six IVFC levels, RomFS index).
  Changed since the copy: imports stay `from extract_exefs import ...` (the parameterized copy above)
  and `program_nca` is called with the new `--title`; otherwise unchanged.
