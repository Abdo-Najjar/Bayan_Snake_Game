"""Settings: volumes, full screen, difficulty, language and progress reset."""
import pygame

from .. import config
from ..config import W
from ..graphics.art import background
from ..graphics.ui import MenuList, overlay
from .base import Scene

VOLUME_STEP = 0.1


class SettingsScene(Scene):
    def __init__(self, app, back):
        super().__init__(app)
        self.back = back            # scene to return to
        self.music = getattr(back, "music", "menu")
        self.menu = MenuList(self.items, W / 2, 140, width=460, height=48, gap=10)
        self.confirm_reset = False
        self.notice = 0.0

    def items(self):
        tr, save = self.app.tr, self.app.save
        on_off = tr.raw("settings.on") if self.app.fullscreen else tr.raw("settings.off")
        diff = tr.raw(f"difficulty.{config.DIFFICULTY_KEYS[save['difficulty']]}")
        reset_key = "settings.reset_confirm" if self.confirm_reset else "settings.reset"
        return [
            ("music", tr("settings.music", v=round(save["music_vol"] * 100))),
            ("sfx", tr("settings.sfx", v=round(save["sfx_vol"] * 100))),
            ("fullscreen", tr("settings.fullscreen", v=on_off)),
            ("difficulty", tr("settings.difficulty", v=diff)),
            ("language", tr("settings.language", v=self.app.tr.language_name())),
            ("reset", tr(reset_key)),
            ("back", tr("settings.back")),
        ]

    def change(self, key, step):
        app, save = self.app, self.app.save
        if key == "music":
            save["music_vol"] = round(min(1.0, max(0.0, save["music_vol"] + step * VOLUME_STEP)), 2)
            app.music.set_volume(save["music_vol"])
        elif key == "sfx":
            save["sfx_vol"] = round(min(1.0, max(0.0, save["sfx_vol"] + step * VOLUME_STEP)), 2)
            app.sfx.set_volume(save["sfx_vol"])
        elif key == "fullscreen":
            app.toggle_fullscreen()
        elif key == "difficulty":
            save["difficulty"] = (save["difficulty"] + step) % len(config.DIFFICULTY_KEYS)
        elif key == "language":
            app.set_language(app.tr.next_language(step))
        else:
            return
        app.sfx.play("click")
        save.write()

    def leave(self):
        self.app.save.write()
        self.app.go(self.back)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.leave()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.leave()
            return
        result = self.menu.handle_event(e)
        if not result:
            return
        key, action = result
        if action == "move":
            self.confirm_reset = False
            self.app.sfx.play("click")
        elif action in ("left", "right"):
            self.change(key, -1 if action == "left" else 1)
        elif action == "activate":
            if key == "back":
                self.leave()
            elif key == "reset":
                if self.confirm_reset:
                    self.app.save.reset_progress()
                    self.app.save.write()
                    self.confirm_reset = False
                    self.notice = 2.0
                    self.app.sfx.play("hit")
                else:
                    self.confirm_reset = True
                    self.app.sfx.play("denied")
            else:
                self.change(key, 1)

    def update(self, dt):
        super().update(dt)
        self.notice = max(0.0, self.notice - dt)

    def draw(self, surf):
        text, tr = self.app.text, self.app.tr
        surf.blit(background("grass"), (0, 0))
        overlay(surf, 140)
        text.draw(surf, tr("settings.title"), text.big, (255, 220, 240), (W / 2, 70))
        self.menu.draw(surf, text, self.t, text.small)
        if self.notice:
            text.draw(surf, tr("settings.reset_done"), text.mid, (255, 160, 160), (W / 2, 560))
        text.draw(surf, tr("settings.footer"), text.small, (230, 230, 230), (W / 2, 605))
