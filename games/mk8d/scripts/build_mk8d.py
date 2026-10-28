#!/usr/bin/env python3
"""Build the isolated Mario Kart 8 Deluxe 4.0.1 macOS target from original local inputs."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

GAME = Path(__file__).resolve().parents[1]
TITLE, UPDATE = '0100152000022000', '0100152000022800'
VERSION = 'v1507328'   # 4.0.1
APP_NAME = 'Mario Kart 8 Deluxe'
BUNDLE_ID = 'org.macnativegames.mk8d'
LIBHAC_SHA256 = '1431267861db5ff68216315b164f10c0edab4df162cedf5429bf8a143b76de19'
PREBUILT = {'dmsh_xlate': 'dm/gfx/tools/dmsh_xlate_bin', 'spirv_cross': 'dm/gfx/tools/spirv_cross_bin'}
LANGUAGES = ('en-US', 'en-GB', 'ja', 'fr', 'de', 'es-419', 'es', 'it', 'nl', 'fr-CA', 'pt', 'ru', 'ko', 'zh-Hant', 'zh-Hans')


def copy_tree(source, destination):
    """Copy source files without removing tables a previous build generated in the workspace."""
    for src in sorted(source.rglob('*')):
        if (not src.is_file() or any(part in ('__pycache__', 'gen', 'obj', 'bin') or part.endswith('.dSYM')
                                     for part in src.relative_to(source).parts)):
            continue
        dst = destination / src.relative_to(source)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file() or src.read_bytes() != dst.read_bytes():
            shutil.copy2(src, dst)


def verify_prebuilt():
    root = GAME / 'prebuilt/macos-arm64'
    expected = set()
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, rel = line.split('  ', 1)
        expected.add(rel)
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != digest:
            raise ValueError(f'prebuilt tool checksum mismatch: {rel}')
    actual = {str(p.relative_to(root)) for name in PREBUILT for p in (root / name).rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError('prebuilt tool file set differs from SHA256SUMS')


def prepare_offline_dependencies(work, package):
    """Accept an explicit local prerequisite; never download or use a global cache."""
    package = package.expanduser().resolve()
    if not package.is_file():
        raise ValueError('local LibHac 0.19.0 package is missing; see README.md')
    if hashlib.sha256(package.read_bytes()).hexdigest() != LIBHAC_SHA256:
        raise ValueError('LibHac 0.19.0 package SHA-256 mismatch')
    feed = work / 'dependencies/nuget'
    feed.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, feed / 'libhac.0.19.0.nupkg')
    return feed


def stage(work, feed):
    """Keep all generated code, tables and caches outside the checkout."""
    source = work / 'source'
    verify_prebuilt()
    copy_tree(GAME / 'runtime', source / 'dm')
    for name, rel in PREBUILT.items():
        copy_tree(GAME / 'prebuilt/macos-arm64' / name, source / rel)
        for exe in ('dmsh_xlate', 'spirv-cross'):
            if (source / rel / exe).is_file():
                (source / rel / exe).chmod(0o755)
    copy_tree(GAME / 'assets', source / 'assets')
    target = source / 'scripts/build_ipa_from_nsp.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GAME / 'third_party/nxnative/build_ipa_from_nsp.py', target)
    # nx_extract restores LibHac from this folder only: NuGet reads the nearest NuGet.Config above the project, and <clear/> drops every inherited feed and fallback folder.
    (source / 'NuGet.Config').write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<configuration>\n'
        f'  <packageSources><clear /><add key="mk8d-local" value="{feed}" /></packageSources>\n'
        '  <fallbackPackageFolders><clear /></fallbackPackageFolders>\n</configuration>\n')
    return source


def pfs0_names(path):
    """The file names in an NSP's PFS0 header (no keys needed: the ticket's name is its rights ID, whose first 16 digits are the title ID)."""
    with path.open('rb') as f:
        head = f.read(16)
        if len(head) < 16 or head[:4] != b'PFS0':
            return None
        count, strings = struct.unpack_from('<II', head, 4)
        if count > 4096 or strings > 1 << 20:
            return None
        table = f.read(count * 24 + strings)
    names = table[count * 24:]
    out = []
    for i in range(count):
        offset = struct.unpack_from('<I', table, i * 24 + 16)[0]
        end = names.find(b'\0', offset)
        out.append(names[offset:end if end >= 0 else None].decode('utf-8', 'replace'))
    return out


def classify(path):
    """'base', 'update' or None, from the NSP's ticket (else its [title ID] tag), and the [v…] tag of the name."""
    names = pfs0_names(path)
    if names is None:
        return None, None
    tickets = {n[:16].upper() for n in names if re.fullmatch(r'[0-9A-Fa-f]{32}\.tik', n)}
    tag = re.search(r'\[([0-9A-Fa-f]{16})\]', path.name)
    title = (tickets.pop() if len(tickets) == 1 else None) or (tag.group(1).upper() if tag and not tickets else None)
    version = re.search(r'\[(v\d+)\]', path.name)
    return {TITLE: 'base', UPDATE: 'update'}.get(title), version.group(1) if version else None


def link_inputs(inputs, work):
    """Link the base game and the 4.0.1 update, under names that carry their title and version tags. Everything else, such as add-on content, is left out."""
    destination = work / 'input'
    destination.mkdir(parents=True, exist_ok=True)
    picks, skipped = {}, []
    for path in sorted(inputs.iterdir()):
        if path.name.startswith('._') or path.suffix.lower() != '.nsp' or not path.is_file():
            continue
        kind, version = classify(path)
        if kind == 'update' and version not in (None, VERSION):
            raise ValueError(f'this target supports only the 4.0.1 update ({VERSION}); remove or move {path.name}')
        if kind is None:
            skipped.append(path.name)
            continue
        if kind in picks:
            raise ValueError(f'more than one {kind} NSP in the input folder: {picks[kind].name}, {path.name}')
        picks[kind] = path.resolve()
    for kind in ('base', 'update'):
        if kind not in picks:
            raise ValueError(f'the input folder has no Mario Kart 8 Deluxe {"base game" if kind == "base" else "4.0.1 update"} NSP')
    for name in skipped:
        print(f'ignored (not the base game or the 4.0.1 update): {name}', flush=True)
    wanted = {f'{APP_NAME} [{TITLE}][v0].nsp': picks['base'], f'{APP_NAME} [{UPDATE}][{VERSION}].nsp': picks['update']}
    for old in destination.iterdir():
        if old.is_symlink() and old.name not in wanted:
            old.unlink()
    for name, src in wanted.items():
        dst = destination / name
        if dst.is_symlink() and dst.resolve() == src:
            continue
        if dst.exists() or dst.is_symlink():
            raise ValueError(f'refusing to replace an existing input: {dst}')
        dst.symlink_to(src)
    return destination


def environment(work):
    env = dict(os.environ, DM_GAME=TITLE, TMPDIR=str(work / 'tmp'), NUGET_PACKAGES=str(work / 'cache/nuget'),
               DOTNET_CLI_HOME=str(work / 'cache/dotnet'), PYTHONDONTWRITEBYTECODE='1',
               DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_NOLOGO='1',
               DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true', NuGetAudit='false', MACOSX_DEPLOYMENT_TARGET='26.0')   # NuGetAudit: MSBuild reads it from the environment; no vulnerability feed is queried
    for key in ('TMPDIR', 'NUGET_PACKAGES', 'DOTNET_CLI_HOME'):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, help='folder with the base NSP and the 4.0.1 update NSP (other files are ignored)')
    parser.add_argument('--keys', required=True, type=Path, help='your local prod.keys (never copied into the app)')
    parser.add_argument('--libhac-package', required=True, type=Path, help='local LibHac 0.19.0 .nupkg (SHA-256 pinned; no download)')
    parser.add_argument('--work-dir', required=True, type=Path, help='private build directory outside the checkout')
    parser.add_argument('--output', required=True, type=Path, help='new .app output path')
    parser.add_argument('--language', default='en-US', choices=LANGUAGES, help='game language (default en-US)')
    args = parser.parse_args()
    work, output = args.work_dir.expanduser().resolve(), args.output.expanduser().resolve()
    if output.suffix != '.app':
        parser.error('--output must end in .app')
    if output.exists():
        parser.error(f'output already exists: {output}')
    checkout = GAME.parents[1]
    if any(path == checkout or checkout in path.parents for path in (work, output)):
        parser.error('--work-dir and --output must be outside the checkout to keep game content out of Git')
    if not args.inputs.expanduser().is_dir() or not args.keys.expanduser().is_file():
        parser.error('inputs folder and keys must exist')
    work.mkdir(parents=True, exist_ok=True)
    feed = prepare_offline_dependencies(work, args.libhac_package)
    source = stage(work, feed)
    inputs = link_inputs(args.inputs.expanduser().resolve(), work)
    env = environment(work)
    subprocess.run([sys.executable, str(source / 'scripts/build_ipa_from_nsp.py'), str(inputs),
                    '--keys', str(args.keys.expanduser().resolve()), '--package', VERSION, '--platform', 'mac-app',
                    '--out', str(output), '--app-name', APP_NAME, '--bundle-id', BUNDLE_ID,
                    '--language', args.language, '--progress', 'lines'], env=env, check=True, stdin=subprocess.DEVNULL)
    if not output.is_dir():
        raise ValueError(f'the build finished without an app: {output}')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(output)], check=True)
    print(f'Built {output}\nSaves: ~/Library/Application Support/nxnative/{TITLE}/  Log: ~/Library/Logs/nxnative/{TITLE}.log')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f'error: {error}')
