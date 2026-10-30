"""Base class for every screen in the game."""
import pygame


class Scene:
    music = "menu"          # background track while this scene is shown
    show_cursor = True

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def enter(self):
        """Called every time the scene becomes active (also when returning to it)."""
        self.app.music.play(self.music)
        pygame.mouse.set_visible(self.show_cursor)

    def handle_event(self, event):
        pass

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        pass
