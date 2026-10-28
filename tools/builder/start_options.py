"""Start options for the latest versions (S5.1, P1-P5): what each choice sets, where the choices are kept, and Play.
The model: no Tk.

Only TOTK 1.4.3 (`v143`) and BotW 1.9.0 (`botw190`). Every choice is a closed list whose values the game's own parsers
take (tests/test_builder_start_drift.py reads them). "auto" sets nothing: the game decides, as without the builder.
Choices that only work when the game is started with Play (environment variables through `open --env`) are kept per game
in Builder/start-options.json; 1.4.3's picture is the game's own picture-mode.txt (kept for a Finder start too; key 3 in
the game overwrites it), written only while the game is not running. A player who sets TOTK_PICTURE_MODE or
TOTK_GAME_SLOT_DIR by hand moves the game's files elsewhere; the builder keeps looking at the default places."""
from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path

from tools.builder import game_state
from tools.builder.ports import Outcome

PLAY, FILE = 'play', 'file'         # how a choice reaches the game: Play's environment, or the game's own file
OPEN_S = 30.0


@dataclass(frozen=True)
class Option:
    id: str
    how: str
    choices: tuple                  # choice ids; the first is "auto"


V143 = (Option('picture', FILE, ('auto', 'metalfx', 'native-2k')),
        Option('interpolation', PLAY, ('auto', 'interp30', 'interp', 'interpmax')),
        Option('smoothing', PLAY, ('auto', 'on')),
        Option('ground', PLAY, ('auto', '16')),
        Option('aspect', PLAY, ('auto', '21:9')))
BOTW190 = (Option('picture', PLAY, ('auto', 'metalfx')),
           Option('interpolation', PLAY, ('auto', 'interp30', 'interp', 'interpmax')),
           Option('smoothing', PLAY, ('auto', 'on')),
           Option('ground', PLAY, ('auto', '16')))
OPTIONS = {'v143': V143, 'botw190': BOTW190}
ENV = {('interpolation', c): {'TOTK_MFX': c} for c in ('interp30', 'interp', 'interpmax')}
ENV.update({('picture', 'metalfx'): {'TOTK_MFX_UPSCALE': '1', 'TOTK_MFX_OUTPUT': '1'},     # BotW only: PLAY there
            ('smoothing', 'on'): {'TOTK_TAA': '1'}, ('ground', '16'): {'TOTK_ANISO': '16'},
            ('aspect', '21:9'): {'TOTK_ASPECT': '21:9'}})
PICTURE_WORDS = {'metalfx': 'metalfx', 'native-2k': 'native-2k', 'native-4k': 'native-2k', 'off': 'auto'}


@dataclass(frozen=True)
class StartPaths:
    store: Path                     # Builder/start-options.json
    data: Path                      # ~/Library/Application Support/MacNativeGames (the games' folders inside)


@dataclass(frozen=True)
class StartState:
    game: str
    app: Path | None
    version: str | None
    reason: str = ''                # '' or why the tab cannot offer options: no_game_file, no_app, unknown_version
    options: tuple = ()
    choices: dict = field(default_factory=dict)
    notes: tuple = ()               # one-line notes: a broken store, an unknown picture word, the game running
    name: str = ''                  # the game's display name, for the tab's title
    version_label: str = ''         # the version as players know it (1.4.3), '' when unknown


@dataclass(frozen=True)
class PlayResult:
    ok: bool
    reason: str = ''                # '' or: running, no_app, unknown_version, open_failed
    detail: str = ''
    env: dict = field(default_factory=dict)
    held: tuple = ()                # chosen options not passed: ('interpolation',) while the GPU has not said yes


GPU_OK = ('yes', 'unknown')         # interpolation is passed only after the GPU said yes, or "unknown" was shown


def picture_file(spec, paths):
    return paths.data / spec.data_folder / 'picture-mode.txt'


def _load_store(path):
    try:
        data = json.loads(Path(path).read_text())
        return (data.get('games') if isinstance(data, dict) and isinstance(data.get('games'), dict) else {}), ()
    except FileNotFoundError:
        return {}, ()
    except (OSError, ValueError) as e:
        return {}, (f'start-options.json could not be read ({e.__class__.__name__}): automatic settings',)


def _write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    partial.write_text(content)
    os.replace(partial, path)


def read_picture(path):
    """1.4.3's picture choice from the game's file: (choice, note)."""
    try:
        word = Path(path).read_text().strip()
    except FileNotFoundError:
        return 'auto', ''
    except OSError as e:
        return 'auto', f'{path} could not be read ({e.__class__.__name__})'
    if word in PICTURE_WORDS:
        return PICTURE_WORDS[word], ''
    return 'auto', f'picture-mode.txt holds "{word[:40]}", which the game reads as off'


def read_state(spec, app, paths):
    state = _read_state(spec, app, paths)
    label = next((v.display for v in spec.versions if v.key == state.version), '')
    return replace(state, name=spec.display_name, version_label=label)


def _read_state(spec, app, paths):
    if app is None:
        return StartState(spec.id, None, None, 'no_game_file')
    version = game_state.app_version(app)
    if not Path(app).is_dir():
        return StartState(spec.id, app, None, 'no_app')
    if version not in OPTIONS:
        return StartState(spec.id, app, version, 'unknown_version')
    games, notes = _load_store(paths.store)
    saved = games.get(spec.id) if isinstance(games.get(spec.id), dict) else {}
    choices = {}
    for option in OPTIONS[version]:
        if option.how == FILE:
            choices[option.id], note = read_picture(picture_file(spec, paths))
            notes += (note,) if note else ()
        else:
            value = saved.get(option.id, 'auto')
            choices[option.id] = value if value in option.choices else 'auto'
    return StartState(spec.id, app, version, '', OPTIONS[version], choices, notes)


def choose(spec, app, paths, option_id, choice):
    """Keep one choice; the new state. ValueError for an option or choice outside the table."""
    state = read_state(spec, app, paths)
    option = next((o for o in state.options if o.id == option_id), None)
    if option is None or choice not in option.choices:
        raise ValueError(f'no choice {choice!r} for {option_id!r} on {state.version}')
    if option.how == FILE:
        if game_state.game_running(paths.data / spec.data_folder):
            return _with_note(read_state(spec, app, paths), 'running')
        target = picture_file(spec, paths)
        if choice == 'auto':
            target.unlink(missing_ok=True)
        else:
            _write(target, choice + '\n')
    else:
        games, _ = _load_store(paths.store)
        mine = dict(games.get(spec.id) or {})
        if choice == 'auto':
            mine.pop(option_id, None)
        else:
            mine[option_id] = choice
        games = {**games, spec.id: mine}
        _write(paths.store, json.dumps({'format': 1, 'games': games}, indent=2) + '\n')
    return read_state(spec, app, paths)


def _with_note(state, note):
    return replace(state, notes=state.notes + (note,))


def held_back(state, gpu):
    """Chosen options Play must not pass now: interpolation unless the GPU said yes or the warning for "unknown" was
    shown (while it is still being checked, or after "no", the game could stop at start)."""
    chosen = state.choices.get('interpolation', 'auto') != 'auto'
    return ('interpolation',) if chosen and gpu not in GPU_OK else ()


def env_for(state, gpu):
    """The environment Play passes: the PLAY choices that are not auto, less what held_back keeps."""
    env, held = {}, held_back(state, gpu)
    for option in state.options:
        choice = state.choices.get(option.id, 'auto')
        if option.how != PLAY or choice == 'auto' or option.id in held:
            continue
        env.update(ENV[(option.id, choice)])
    return env


def play(runner, spec, app, paths, gpu):
    state = read_state(spec, app, paths)
    if state.reason:
        return PlayResult(False, state.reason)
    if game_state.game_running(paths.data / spec.data_folder):
        return PlayResult(False, 'running')
    env = env_for(state, gpu)
    argv = ['/usr/bin/open'] + [a for k, v in sorted(env.items()) for a in ('--env', f'{k}={v}')] + [str(app)]
    result = runner.run(argv, timeout_s=OPEN_S)
    if result.outcome is not Outcome.OK:
        return PlayResult(False, 'open_failed', (result.stderr or result.outcome.name).strip()[-300:], env)
    return PlayResult(True, env=env, held=held_back(state, gpu))
