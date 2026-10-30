"""Headless tests: python -m unittest discover tests"""
import json
import math
import os
import sys
import tempfile
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
_tmp = tempfile.mkdtemp()
os.environ["BAYAN_SAVE_FILE"] = os.path.join(_tmp, "save.json")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
from pygame import Vector2 as V  # noqa: E402

from bayan_game import config  # noqa: E402
from bayan_game.app import App  # noqa: E402
from bayan_game.content.levels import LEVELS, TERRAINS  # noqa: E402
from bayan_game.content.shop import SHOP_ITEMS  # noqa: E402
from bayan_game.core.i18n import _flatten  # noqa: E402
from bayan_game.entities.boss import Boss  # noqa: E402
from bayan_game.entities.obstacles import Rock  # noqa: E402

DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def load_lang(code):
    with open(os.path.join(config.LANG_DIR, f"{code}.json"), encoding="utf-8") as f:
        return _flatten(json.load(f))


class LanguageFiles(unittest.TestCase):
    def test_languages_have_same_keys(self):
        en, ar = load_lang("en"), load_lang("ar")
        self.assertEqual(set(en) - set(ar), set(), "missing in ar.json")
        self.assertEqual(set(ar) - set(en), set(), "missing in en.json")

    def test_content_has_translations(self):
        en = load_lang("en")
        for i in range(len(LEVELS)):
            self.assertIn(f"level_tips.{i}", en)
        for t in TERRAINS:
            self.assertIn(f"terrain.{t}", en)
        for it in SHOP_ITEMS:
            self.assertIn(f"items.{it['id']}", en)

    def test_no_arabic_in_code(self):
        root = os.path.dirname(config.PACKAGE_DIR)
        for folder, _, files in os.walk(root):
            if ".git" in folder:
                continue
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(folder, name), encoding="utf-8") as f:
                        src = f.read()
                    self.assertFalse(any(0x600 <= ord(ch) <= 0x6FF for ch in src), name)


class GameFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.save["fullscreen"] = False

    def run_frames(self, n, events=()):
        for i in range(n):
            self.app.step(DT, list(events) if i == 0 else [])
            if i % 10 == 0:
                self.app.draw()

    def test_menu_screens_draw_in_both_languages(self):
        app = self.app
        for code in ("ar", "en"):
            app.set_language(code)
            for show in (app.show_menu, app.show_levels, app.show_shop, app.show_victory):
                show()
                self.run_frames(30)
            app.show_settings(back=app.scene)
            self.run_frames(30)
        app.set_language("ar")

    def test_play_every_level(self):
        app = self.app
        app.save["unlocked"] = len(LEVELS)
        for i in range(len(LEVELS)):
            app.start_level(i)
            game = app.scene
            self.run_frames(200)
            self.assertEqual(game.state, "play")
            frames = 0
            while game.state == "play" and frames < 6000:
                frames += 1
                game.bayan.invuln = 1.0
                if game.boss:
                    game.boss.hp = 0 if frames > 120 else game.boss.hp
                elif game.gem is not None:
                    game.bayan.pos.update(game.gem)
                game.update_play(DT, V(1, 0))
                game.t += DT
                if frames % 15 == 0:
                    app.draw()
            self.assertEqual(game.state, "done", f"level {i + 1}")
            self.assertGreaterEqual(app.save.stars(i), 1)
            self.run_frames(60)
        self.assertGreater(app.save["coins"], 0)

    def test_standing_still_loses(self):
        app = self.app
        app.start_level(0)
        game = app.scene
        self.run_frames(200)
        frames = 0
        while game.state == "play" and frames < 60 * 60:
            frames += 1
            game.update_play(DT, V())
            game.t += DT
        self.assertEqual(game.state, "over")
        self.run_frames(60)                            # menu ignores keys for a moment
        self.run_frames(1, [key(pygame.K_RETURN)])     # "try again"
        self.assertEqual(app.scene.state, "intro")

    def test_pause_menu(self):
        app = self.app
        app.start_level(0)
        self.run_frames(200)
        self.run_frames(1, [key(pygame.K_p)])
        self.assertEqual(app.scene.state, "paused")
        self.run_frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(app.scene.state, "play")

    def test_boss_loses_hp_on_rock(self):
        cfg = LEVELS[-1]
        boss = Boss(V(200, 300), cfg)
        rock = Rock(500, 300, 35)

        class Target:
            pos, vel = V(800, 300), V()

        boss.place(V(200, 300), V(800, 300))
        boss.mode, boss.mode_t = "charge", 2.0
        events = []
        for _ in range(120):
            events += boss.update(DT, Target, True, [rock], [], 0)
        self.assertIn("boss_hit", [e for e, _ in events])
        self.assertEqual(boss.hp, config.BOSS_HP - 1)
        self.assertFalse(boss.harmful)

    def test_shop_buy_and_equip(self):
        app = self.app
        app.save["coins"] = 1000
        app.show_shop()
        shop = app.scene
        shop.sel = next(i for i, it in enumerate(SHOP_ITEMS) if it["id"] == "crown")
        shop.choose()
        self.assertTrue(app.save.owns("crown"))
        self.assertEqual(app.save["hat"], "crown")
        self.assertEqual(app.save["coins"], 1000 - 100)

    def test_settings_change_values(self):
        app = self.app
        app.show_settings(back=app.scene)
        s = app.scene
        vol = app.save["music_vol"]
        s.change("music", -1)
        self.assertAlmostEqual(app.save["music_vol"], max(0.0, vol - 0.1))
        lang = app.tr.code
        s.change("language", 1)
        self.assertNotEqual(app.tr.code, lang)
        s.change("language", 1)
        self.assertEqual(app.tr.code, lang)
        self.assertTrue(math.isfinite(app.save["difficulty"]))


if __name__ == "__main__":
    unittest.main()
