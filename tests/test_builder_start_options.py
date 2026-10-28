"""tools/builder/start_options.py and game_state.py (S5.1): the options table, the store, 1.4.3's picture file, the
app's version, the running-game test, the GPU probe and Play, on fake apps and slots in a temporary folder."""
import fcntl
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.builder import game_state, start_options
from tools.builder.games import BOTW, TOTK
from tools.builder.ports import CommandResult, Outcome
from tools.builder.start_options import StartPaths, choose, env_for, play, read_picture, read_state


class Runner:
    def __init__(self, outcome=Outcome.OK, stdout=''):
        self.calls, self.outcome, self.stdout = [], outcome, stdout

    def run(self, argv, timeout_s):
        self.calls.append((list(argv), timeout_s))
        return CommandResult(self.outcome, 0 if self.outcome is Outcome.OK else 1, self.stdout, 'boom', 0.0, 1, True)


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.tmp = Path(tmp)
        self.paths = StartPaths(self.tmp / 'Builder/start-options.json', self.tmp / 'data')

    def app(self, *versions, name='Tears of the Kingdom.app'):
        app = self.tmp / name
        for version in versions:
            (app / 'Contents/Resources/totk/extracted' / version).mkdir(parents=True)
        return app

    def hold_slot(self, game_folder, owner='user', pid=None):
        """The slot's lock held through a second open (flock clashes between opens on macOS), and its holder."""
        slot = self.paths.data / game_folder / 'game-slot'
        slot.mkdir(parents=True)
        (slot / 'lock').write_text('')
        fd = os.open(slot / 'lock', os.O_RDONLY)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (slot / 'holder').write_text(f'owner={owner}\ngame_pid={pid or os.getpid()}\ngame_start=1\n')


class Version(Base):
    def test_the_one_entry_besides_firmware(self):
        self.assertEqual(game_state.app_version(self.app('firmware', 'v143')), 'v143')

    def test_two_versions_or_none_are_unknown(self):
        self.assertIsNone(game_state.app_version(self.app('v0', 'v143')))
        self.assertIsNone(game_state.app_version(self.app('firmware', name='Other.app')))
        self.assertIsNone(game_state.app_version(self.tmp / 'missing.app'))

    def test_reasons(self):
        self.assertEqual(read_state(TOTK, None, self.paths).reason, 'no_game_file')
        self.assertEqual(read_state(TOTK, self.tmp / 'missing.app', self.paths).reason, 'no_app')
        self.assertEqual(read_state(TOTK, self.app('v121'), self.paths).reason, 'unknown_version')


class Running(Base):
    def test_no_slot_or_a_free_lock(self):
        self.assertFalse(game_state.game_running(self.paths.data / 'TOTK'))
        slot = self.paths.data / 'TOTK/game-slot'
        slot.mkdir(parents=True)
        (slot / 'lock').write_text('')
        (slot / 'holder').write_text(f'owner=user\ngame_pid={os.getpid()}\n')
        self.assertFalse(game_state.game_running(self.paths.data / 'TOTK'))

    def test_a_held_lock_with_a_player_game(self):
        self.hold_slot('TOTK')
        self.assertTrue(game_state.game_running(self.paths.data / 'TOTK'))

    def test_a_held_lock_by_a_test_or_a_dead_pid_is_not_a_player_game(self):
        self.hold_slot('TOTK', owner='agent')
        self.assertFalse(game_state.game_running(self.paths.data / 'TOTK'))
        self.hold_slot('BotW', pid=2 ** 22 - 7)                         # no such process
        self.assertFalse(game_state.game_running(self.paths.data / 'BotW'))


class Probe(unittest.TestCase):
    def test_answers_and_the_long_timeout(self):
        for outcome, stdout, answer in ((Outcome.OK, 'true\n', 'yes'), (Outcome.OK, 'warning\nfalse\n', 'no'),
                                        (Outcome.OK, 'gibberish', 'unknown'), (Outcome.TIMEOUT, '', 'unknown')):
            runner = Runner(outcome, stdout)
            self.assertEqual(game_state.probe_metal4fx(runner), answer)
            self.assertEqual((runner.calls[0][0][:3], runner.calls[0][1]), (['/usr/bin/xcrun', 'swift', '-e'], 120.0))


class Choices(Base):
    def test_automatic_by_default_and_a_choice_is_kept(self):
        app = self.app('firmware', 'v143')
        self.assertEqual(set(read_state(TOTK, app, self.paths).choices.values()), {'auto'})
        state = choose(TOTK, app, self.paths, 'interpolation', 'interp')
        self.assertEqual(state.choices['interpolation'], 'interp')
        self.assertEqual(read_state(TOTK, app, self.paths).choices['interpolation'], 'interp')
        self.assertEqual(choose(TOTK, app, self.paths, 'interpolation', 'auto').choices['interpolation'], 'auto')
        self.assertNotIn('interpolation', self.paths.store.read_text())

    def test_only_the_tables_choices(self):
        botw = self.app('botw190', name='Breath of the Wild.app')
        self.assertRaises(ValueError, choose, BOTW, botw, self.paths, 'aspect', '21:9')         # 1.4.3 only
        self.assertRaises(ValueError, choose, BOTW, botw, self.paths, 'interpolation', 'fast')

    def test_a_broken_or_strange_store_reads_as_automatic(self):
        app = self.app('v143')
        self.paths.store.parent.mkdir(parents=True)
        self.paths.store.write_text('{"games": {"totk": {"interpolation": "warp"}}}')
        self.assertEqual(read_state(TOTK, app, self.paths).choices['interpolation'], 'auto')
        self.paths.store.write_text('{"games": {"totk": {"aspect": "display"}}}')    # dropped upstream 2026-10-25
        self.assertEqual(read_state(TOTK, app, self.paths).choices['aspect'], 'auto')
        self.paths.store.write_text('{not json')
        state = read_state(TOTK, app, self.paths)
        self.assertEqual((state.choices['interpolation'], len(state.notes)), ('auto', 1))


class Picture(Base):
    def test_1_4_3s_picture_is_the_games_own_file(self):
        app, path = self.app('v143'), start_options.picture_file(TOTK, self.paths)
        choose(TOTK, app, self.paths, 'picture', 'metalfx')
        self.assertEqual(path.read_text(), 'metalfx\n')
        self.assertEqual(env_for(read_state(TOTK, app, self.paths), 'yes'), {})      # no picture variable on 1.4.3
        choose(TOTK, app, self.paths, 'picture', 'auto')
        self.assertFalse(path.exists())

    def test_reading_the_file(self):
        path = self.tmp / 'picture-mode.txt'
        for word, choice in (('native-4k', 'native-2k'), ('off', 'auto'), ('metalfx', 'metalfx')):
            path.write_text(word + '\n')
            self.assertEqual(read_picture(path), (choice, ''))
        path.write_text('sharp\n')
        self.assertEqual(read_picture(path)[0], 'auto')
        self.assertTrue(read_picture(path)[1])

    def test_not_written_while_the_game_runs(self):
        app, path = self.app('v143'), start_options.picture_file(TOTK, self.paths)
        self.hold_slot('TOTK')
        state = choose(TOTK, app, self.paths, 'picture', 'native-2k')
        self.assertEqual((path.exists(), state.notes[-1]), (False, 'running'))


class Play(Base):
    def test_play_passes_the_play_choices(self):
        app = self.app('botw190', name='Breath of the Wild.app')
        for option, choice in (('picture', 'metalfx'), ('interpolation', 'interp30'), ('ground', '16')):
            choose(BOTW, app, self.paths, option, choice)
        runner = Runner()
        result = play(runner, BOTW, app, self.paths, 'yes')
        self.assertTrue(result.ok)
        self.assertEqual(runner.calls[0][0], ['/usr/bin/open', '--env', 'TOTK_ANISO=16', '--env', 'TOTK_MFX=interp30',
                                              '--env', 'TOTK_MFX_OUTPUT=1', '--env', 'TOTK_MFX_UPSCALE=1', str(app)])

    def test_interpolation_only_after_the_gpu_said_yes_or_unknown(self):
        app = self.app('v143')
        choose(TOTK, app, self.paths, 'interpolation', 'interpmax')
        state = read_state(TOTK, app, self.paths)
        for gpu in ('no', 'checking', None):                            # B1: still being checked holds it back too
            self.assertEqual(env_for(state, gpu), {})
        for gpu in ('yes', 'unknown'):
            self.assertEqual(env_for(state, gpu), {'TOTK_MFX': 'interpmax'})
        result = play(Runner(), TOTK, app, self.paths, 'checking')
        self.assertEqual((result.ok, result.env, result.held), (True, {}, ('interpolation',)))
        self.assertEqual(play(Runner(), TOTK, app, self.paths, 'yes').held, ())

    def test_refusals(self):
        app = self.app('v143')
        self.hold_slot('TOTK')
        runner = Runner()
        self.assertEqual(play(runner, TOTK, app, self.paths, 'yes').reason, 'running')
        self.assertEqual(play(runner, TOTK, self.tmp / 'gone.app', self.paths, 'yes').reason, 'no_app')
        self.assertEqual(runner.calls, [])

    def test_open_failing(self):
        app = self.app('v143')
        result = play(Runner(Outcome.NONZERO), TOTK, app, self.paths, 'yes')
        self.assertEqual((result.ok, result.reason, result.detail), (False, 'open_failed', 'boom'))


if __name__ == '__main__':
    unittest.main()
