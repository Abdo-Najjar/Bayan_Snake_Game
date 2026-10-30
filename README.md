# Bayan vs the Snake

A pygame chase game: help Bayan collect gems across 9 levels while snakes hunt her down,
then defeat the giant snake in its lair.

## Run

```bash
pip install -r requirements.txt
python main.py
```

Or double-click `run_game.bat` on Windows. `python -m bayan_game` also works.

## Controls

| Key | Action |
|---|---|
| Arrows / WASD | Move |
| Space / Shift | Dash (Bayan can't be caught while dashing) |
| P / Esc | Pause |
| F11 | Toggle full screen |
| Mouse | Menus, shop, settings |

## Features

- 9 levels across 5 terrains: meadow, desert (quicksand), snow (slippery), forest (bushes to hide in), and the boss lair
- 4 snake types: normal, small & fast, lunger (telegraphs then lunges), poison (leaves slowing puddles)
- Boss fight: the giant snake charges in a straight line; make it crash into rocks 3 times
- Power-ups: speed, shield, freeze, invisibility
- 1-3 stars per level, coins, and an outfit shop (dresses, bow, flower, cap, hijab, crown)
- Settings: music / sound volume, full screen, difficulty, language
- Music and sound effects are generated in code, so there are no audio files
- Arabic and English, and more languages can be added through JSON files

## Project structure

```
main.py                     entry point
bayan_game/
  app.py                    window, main loop, scene switching
  config.py                 tuning constants and paths
  utils.py                  small math helpers
  assets/lang/              translations: en.json, ar.json
  content/
    levels.py               level layouts and snake types
    shop.py                 shop items
  core/
    audio.py                generated sound effects and music
    i18n.py                 translation loader (+ Arabic shaping)
    save.py                 progress and settings (save.json)
    text.py                 fonts and cached text rendering
  entities/
    bayan.py                the player
    snake.py                chasing snakes
    boss.py                 the giant snake
    obstacles.py            rocks, quicksand, poison, bushes
    pickups.py              power-ups
    effects.py              particles and floating text
  graphics/
    art.py                  backgrounds and icons
    hud.py                  in-game top bar
    ui.py                   buttons, panels, overlays
  scenes/
    main_menu.py  level_select.py  shop.py  settings.py
    gameplay.py   victory.py       base.py
tests/
  test_game.py              headless tests
```

## Adding a language

1. Copy `bayan_game/assets/lang/en.json` to e.g. `fr.json`.
2. Set `_meta.name` (shown in Settings) and `_meta.rtl` (`true` for right-to-left scripts).
3. Translate the values and keep the keys. `{placeholders}` must stay as they are.

The new language shows up in Settings automatically. Missing keys fall back to English.

## Adding or tuning a level

Edit `LEVELS` in `bayan_game/content/levels.py`, then add a `level_tips.<index>` entry to every
language file. Global tuning (speeds, power-up durations, rewards) lives in `bayan_game/config.py`.

## Tests

```bash
python -m unittest discover tests
```

The tests run without a window. They play through every level, check that the language files
have matching keys, and check that no Arabic text sits in the Python code.

Progress is saved in `save.json` (ignored by git). Delete it to start over.
