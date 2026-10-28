"""Drift (S5.1, P1 and gap 6): every value tools/builder/start_options.py can pass or write is one the game's own
parser takes, read from the runtime's sources in this repository, and the app names and data folders the Settings tab
looks for are build_app.py's. A change in the runtime that drops a value fails here, not at a player's start."""
import ast
from pathlib import Path
import re
import unittest

from tools.builder.games import GAMES
from tools.builder.start_options import ENV, FILE, OPTIONS, PICTURE_WORDS

REPO = Path(__file__).resolve().parents[1]
NVN = REPO / 'games/totk/third_party/d2r_gfx/gfx/nvn'
RUNTIME = REPO / 'games/totk/runtime'


def source(path):
    return path.read_text()


class Drift(unittest.TestCase):
    def test_interpolation_words_are_the_parsers(self):
        parser = source(NVN / 'totk_mfx.m')
        words = {v['TOTK_MFX'] for (o, _), v in ENV.items() if o == 'interpolation'}
        self.assertEqual(words, {'interp30', 'interp', 'interpmax'})
        for word in words:
            self.assertIn(f'!strcmp(e, "{word}")', parser)

    def test_on_switches_read_as_not_zero(self):
        for path, name in ((NVN / 'totk_mfx_up.m', 'TOTK_MFX_UPSCALE'), (NVN / 'totk_mfx_up.m', 'TOTK_MFX_OUTPUT'),
                           (NVN / 'totk_taa.m', 'TOTK_TAA')):
            with self.subTest(name=name):
                text = source(path)
                at = text.index(f'getenv("{name}")')
                self.assertRegex(text[at:at + 1000], r'strcmp\(e, "0"\)')     # anything but "0" is on: we pass "1"

    def test_anisotropy_is_clamped_to_16(self):
        self.assertIn('aniso > 16 ? 16', source(NVN / 'nvn_mtl.m'))
        self.assertEqual(ENV[('ground', '16')], {'TOTK_ANISO': '16'})

    def test_aspect_values_parse(self):
        """Every TOTK_ASPECT value is a <w>:<h> / <w>x<h> ratio between 0.5 and 8: the rule aspect_math.h's
        aspect_parse applies (read here, so a changed rule fails too); anything else stops the game. Upstream dropped
        "display" (fitting the window) on 2026-10-25, and the Settings tab with it; a saved "display" reads as auto."""
        parser = source(RUNTIME / 'aspect_math.h')
        parse = parser[parser.index('static inline double aspect_parse'):]
        parse = parse[:parse.index('\n}\n')]
        self.assertNotIn('"display"', parse)
        for piece in ('sscanf(e, "%lf:%lf%c"', 'sscanf(e, "%lfx%lf%c"',
                      'a >= 0.5 && a <= 8'):
            self.assertIn(piece, parse)
        values = {v['TOTK_ASPECT'] for v in ENV.values() if 'TOTK_ASPECT' in v}
        self.assertTrue(values)
        for value in values:
            with self.subTest(value=value):
                ratio = re.fullmatch(r'(\d+(?:\.\d+)?)[:x](\d+(?:\.\d+)?)', value)
                self.assertTrue(ratio and float(ratio[2]) > 0
                                and 0.5 <= float(ratio[1]) / float(ratio[2]) <= 8)
        self.assertNotIn('aspect', {o.id for o in OPTIONS['botw190']})  # offered on 1.4.3 only

    def test_1_4_3_picture_words_are_the_games(self):
        code = source(RUNTIME / 'game_patches_v143.c')
        restore = code[code.index('static void picture_mode_restore'):]
        restore = restore[:restore.index('\n}\n')]
        for word in set(PICTURE_WORDS) | {c for o in OPTIONS['v143'] if o.how == FILE for c in o.choices} - {'auto'}:
            self.assertIn(f'"{word}"', restore)
        self.assertIn('getenv("TOTK_PICTURE_MODE")', restore)

    def test_botw_1_9_0_has_no_native_2k(self):
        code = source(RUNTIME / 'game_patches_botw.c')
        self.assertIn('int runtime_output_res(unsigned *w, unsigned *h) { (void)w; (void)h; return 0; }', code)
        picture = next(o for o in OPTIONS['botw190'] if o.id == 'picture')
        self.assertEqual(picture.choices, ('auto', 'metalfx'))

    def test_version_folders_are_the_runtimes(self):
        header = source(RUNTIME / 'game_version.h')
        for version in OPTIONS:
            self.assertIn(f'#define TOTK_GAME_DIR "{version}"', header)

    def test_app_names_and_data_folders_are_build_apps(self):
        tree = ast.parse(source(REPO / 'build_app.py'))
        apps = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'APPS' for t in n.targets))
        for game_id, spec in GAMES.items():
            name, bundle, folder = apps[game_id]
            self.assertEqual((spec.app_name, spec.bundle_id, spec.data_folder), (name, bundle, folder))
        self.assertTrue(re.search(r'"Library/Application Support/MacNativeGames/" GAME_FOLDER',
                                  source(REPO / 'games/totk/app/launcher.m')))
        self.assertIn('stringByAppendingPathComponent:@"picture-mode.txt"', source(REPO / 'games/totk/app/launcher.m'))


if __name__ == '__main__':
    unittest.main()
