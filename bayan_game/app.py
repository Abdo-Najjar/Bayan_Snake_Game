"""Window, main loop and switching between scenes."""
import os
import random

# Smooth (linear) filtering when the 960x640 picture is scaled to the screen.
# Must be set before the window is created.
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")

import pygame  # noqa: E402

from . import config
from .config import W, H, FPS
from .core.audio import Music, Sfx
from .core.i18n import I18n
from .core.save import SaveData
from .core.text import Text
from .graphics.ui import ConfirmDialog
from .scenes.gameplay import GameplayScene
from .scenes.level_select import LevelSelectScene
from .scenes.main_menu import MainMenuScene
from .scenes.settings import SettingsScene
from .scenes.shop import ShopScene
from .scenes.tutorial import TutorialScene
from .scenes.victory import VictoryScene

WINDOW_TITLE = "Bayan vs the Snake"
FADE_TIME = 0.3


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
        self.music = Music(self.save["music_vol"], self.save["sfx_vol"])

        self._shake = 0.0
        self._fade = 0.0
        self._fade_surf = pygame.Surface((W, H))
        self._label = None
        self.modal = None          # dialog drawn on top of the scene; pauses it
        self._cursor_before_modal = True
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
        self._fade = FADE_TIME
        scene.enter()

    def open_dialog(self, dialog):
        self._cursor_before_modal = pygame.mouse.get_visible()
        pygame.mouse.set_visible(True)
        self.modal = dialog

    def close_dialog(self):
        self.modal = None
        pygame.mouse.set_visible(self._cursor_before_modal)

    def request_quit(self):
        """Ask before quitting. Closing the window twice quits right away."""
        if self.modal is not None and self.modal.title_key == "confirm.quit_title":
            self.quit()
            return
        self.open_dialog(ConfirmDialog(self, "confirm.quit_title", "confirm.quit_text", self.quit))

    def show_menu(self):
        self.go(MainMenuScene(self))

    def show_levels(self, selected=None):
        self.go(LevelSelectScene(self, selected))

    def show_shop(self):
        self.go(ShopScene(self))

    def show_settings(self, back):
        self.go(SettingsScene(self, back))

    def show_tutorial(self, then):
        self.go(TutorialScene(self, then))

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
                self.request_quit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif self.modal:
                self.modal.handle_event(e)
                if self.modal and self.modal.closed:
                    self.close_dialog()
            else:
                self.scene.handle_event(e)
        if self.modal:
            self.modal.update(dt)      # the scene stays frozen behind the dialog
        else:
            self.scene.update(dt)
        self._shake = max(0.0, self._shake - dt)
        self._fade = max(0.0, self._fade - dt)

    def draw(self):
        self.scene.draw(self.canvas)
        if self.modal:
            self.modal.draw(self.canvas)
        if self._fade > 0:
            self._fade_surf.set_alpha(int(255 * self._fade / FADE_TIME))
            self.canvas.blit(self._fade_surf, (0, 0))
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
