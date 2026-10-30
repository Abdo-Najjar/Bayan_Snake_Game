"""Regenerates the game's sprites and audio.

    python -m tools.build_assets            # everything
    python -m tools.build_assets sprites    # only PNG sprites
    python -m tools.build_assets audio      # only music and ambience

Needs the packages in requirements-dev.txt (numpy, scipy). The game itself does not.
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "bayan_game", "assets")


def main(argv):
    what = set(argv) or {"sprites", "audio"}
    pygame.init()
    if "sprites" in what:
        from . import sprites
        start = time.time()
        sprites.build_all(os.path.join(ASSETS, "sprites"))
        print(f"sprites done in {time.time() - start:.1f}s")
    if "audio" in what:
        from . import audio
        start = time.time()
        audio.build_all(ASSETS)
        print(f"audio done in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
