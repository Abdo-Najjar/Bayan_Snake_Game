"""Base class for every screen in the game."""
import pygame


class Scene:
    music = "menu"          # assets/music/<name> played while this scene is shown
    ambience = None         # assets/ambience/<name> looped under it (None = quiet)
    show_cursor = True

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def enter(self):
        """Called every time the scene becomes active (also when returning to it)."""
        self.app.music.play(self.music)
        self.app.music.play_ambience(self.ambience)
        pygame.mouse.set_visible(self.show_cursor)

    def handle_event(self, event):
        pass

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        pass
