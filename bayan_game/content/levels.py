"""Level layouts and snake types. Display text lives in assets/lang/*.json."""

TERRAINS = ("grass", "desert", "snow", "forest", "lair")

SNAKE_TYPES = {
    "normal": dict(speed=1.0, turn=1.0, length=12, head_r=13, colors=((60, 170, 70), (40, 130, 50))),
    "small": dict(speed=1.35, turn=1.35, length=7, head_r=9, colors=((230, 200, 60), (190, 160, 40))),
    "lunger": dict(speed=0.9, turn=1.0, length=12, head_r=13, colors=((220, 80, 60), (170, 50, 40))),
    "poison": dict(speed=0.95, turn=1.0, length=13, head_r=13, colors=((150, 90, 200), (110, 60, 160))),
}

# speed/turn: base snake speed (px/s) and turn rate (rad/s)
# predict: how many seconds ahead of Bayan the snakes aim
# sand/bushes: number of quicksand patches / hiding bushes
# The tip shown before each level is "level_tips.<index>" in the language files.
LEVELS = [
    dict(terrain="grass", snakes=["normal"], speed=115, turn=2.2, gems=5, rocks=0, predict=0.0),
    dict(terrain="grass", snakes=["normal", "small"], speed=118, turn=2.4, gems=7, rocks=3, predict=0.0),
    dict(terrain="desert", snakes=["normal", "lunger"], speed=120, turn=2.5, gems=8, rocks=3, sand=3, predict=0.2),
    dict(terrain="desert", snakes=["lunger", "poison"], speed=122, turn=2.6, gems=9, rocks=3, sand=4, predict=0.2),
    dict(terrain="snow", snakes=["normal", "small"], speed=125, turn=2.6, gems=9, rocks=4, predict=0.3),
    dict(terrain="snow", snakes=["lunger", "poison", "small"], speed=122, turn=2.7, gems=10, rocks=4, predict=0.3),
    dict(terrain="forest", snakes=["normal", "lunger"], speed=135, turn=2.9, gems=10, rocks=3, bushes=5,
         predict=0.4),
    dict(terrain="forest", snakes=["poison", "lunger", "small"], speed=132, turn=3.0, gems=12, rocks=3,
         bushes=5, predict=0.45),
    dict(terrain="lair", snakes=["boss"], speed=105, turn=1.7, gems=0, rocks=7, rock_size=(30, 44),
         predict=0.0),
]


def is_boss_level(index):
    return "boss" in LEVELS[index]["snakes"]
