"""Window, main loop and switching between scenes."""
import random

import pygame

from . import config
from .config import W, H, FPS
from .core.audio import Music, Sfx
from .core.i18n import I18n
from .core.save import SaveData
from .core.text import Text
from .scenes.gameplay import GameplayScene
from .scenes.level_select import LevelSelectScene
from .scenes.main_menu import MainMenuScene
from .scenes.settings import SettingsScene
from .scenes.shop import ShopScene
from .scenes.victory import VictoryScene

WINDOW_TITLE = "Bayan vs the Snake"


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass   # no audio device: play silently

        self.save = SaveData()
        self.fullscreen = bool(self.save["fullscreen"])
        self.screen = self._create_window()
        pygame.display.set_caption(WINDOW_TITLE)
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()

        self.tr = I18n(config.LANG_DIR, self.save["language"], config.FALLBACK_LANGUAGE)
        self.text = Text()
        self.sfx = Sfx(self.save["sfx_vol"])
        self.music = Music(self.save["music_vol"])

        self._shake = 0.0
        self._label = None
        self.running = True
        self.scene = None
        self.show_menu()

    # ---------------------------------------------------------------- window
    def _create_window(self):
        # SCALED keeps the 960x640 picture sharp and letterboxed at any screen size
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        try:
            return pygame.display.set_mode((W, H), flags, vsync=1)
        except pygame.error:
            return pygame.display.set_mode((W, H), flags)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.save["fullscreen"] = self.fullscreen
        self.save.write()
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            self.screen = self._create_window()

    def set_language(self, code):
        self.tr.set_language(code)
        self.save["language"] = self.tr.code
        self._label = None

    def name_label(self):
        """Bayan's name tag, rendered once per language."""
        if self._label is None:
            self._label = self.text.render(self.tr("game.bayan"), self.text.tiny, (255, 255, 255))
        return self._label

    def shake(self, amount):
        self._shake = max(self._shake, amount)

    # ---------------------------------------------------------------- scenes
    def go(self, scene):
        self.scene = scene
        scene.enter()

    def show_menu(self):
        self.go(MainMenuScene(self))

    def show_levels(self, selected=None):
        self.go(LevelSelectScene(self, selected))

    def show_shop(self):
        self.go(ShopScene(self))

    def show_settings(self, back):
        self.go(SettingsScene(self, back))

    def start_level(self, index):
        self.go(GameplayScene(self, index))

    def show_victory(self):
        self.go(VictoryScene(self))

    def quit(self):
        self.running = False

    # ---------------------------------------------------------------- loop
    def step(self, dt, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
            else:
                self.scene.handle_event(e)
        self.scene.update(dt)
        self._shake = max(0.0, self._shake - dt)

    def draw(self):
        self.scene.draw(self.canvas)
        offset = (0, 0)
        if self._shake > 0:
            m = int(self._shake * 25)
            offset = (random.randint(-m, m), random.randint(-m, m))
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, offset)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 1 / 30)
            self.step(dt, pygame.event.get())
            self.draw()
        self.save.write()
        pygame.quit()


def main():
    App().run()
