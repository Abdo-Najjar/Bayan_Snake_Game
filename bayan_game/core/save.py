"""Player progress and settings, stored as JSON next to the game."""
import copy
import json
import os

from .. import config
from ..content.shop import FREE_ITEMS

PROGRESS_DEFAULTS = dict(coins=0, unlocked=1, stars={}, owned=list(FREE_ITEMS), dress="pink", hat="bow",
                         tutorial_done=False)
SETTINGS_DEFAULTS = dict(music_vol=0.6, sfx_vol=0.8, fullscreen=True, difficulty=1,
                         language=config.DEFAULT_LANGUAGE)


class SaveData:
    def __init__(self, path=None):
        self.path = path or config.SAVE_FILE
        self.data = copy.deepcopy({**PROGRESS_DEFAULTS, **SETTINGS_DEFAULTS})
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, ValueError):
            return
        if isinstance(loaded, dict):
            for key, default in self.data.items():
                if key in loaded and isinstance(loaded[key], type(default)):
                    self.data[key] = loaded[key]

    def write(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    # ---- progress helpers
    def stars(self, level_index):
        return int(self.data["stars"].get(str(level_index), 0))

    def record_stars(self, level_index, count):
        if count > self.stars(level_index):
            self.data["stars"][str(level_index)] = count

    def total_stars(self):
        return sum(int(v) for v in self.data["stars"].values())

    def is_unlocked(self, level_index):
        return level_index < self.data["unlocked"]

    def unlock(self, count):
        self.data["unlocked"] = max(self.data["unlocked"], count)

    def owns(self, item_id):
        return item_id in self.data["owned"]

    def reset_progress(self):
        self.data.update(copy.deepcopy(PROGRESS_DEFAULTS))
