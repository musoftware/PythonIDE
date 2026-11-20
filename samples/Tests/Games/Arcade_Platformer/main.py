"""Arcplatformer - a platformer for the arcade library (https://api.arcade.academy).

Arrows / A-D move, Space / Up / W jump, R restarts, Esc quits.  Change the level in LEVEL below:
G grass, D dirt, B brick, ? block, c coin, P player start, F the goal flag.
"""
import os

import arcade

TILE = 32
WIDTH, HEIGHT = 800, 480
GRAVITY = 1.0
SPEED = 4.0
JUMP = 15.0
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

LEVEL = [
    '............................................................',
    '............................................................',
    '............................................................',
    '..............................c.c.c.........................',
    '.............................BBBBBBB........................',
    '...........c.c......................................cc......',
    '..........BBBBB.................?...?..............BBBB.....',
    '......................c.c...............e.c.c.c.............',
    '...................?B?..BBBBBB..........BBBBBBBB............',
    '.................................................BBB..........',
    '....c.c.c.............................................c.c...',
    '..........................................................F.',
    '.P.............e...................e........................',
    'GGGGGGGGGGGGGGGGGGGGGGGG...GGGGGGGGGGGGGGGGG...GGGGGGGGGGGGGG',
    'DDDDDDDDDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDD',
]
TILE_INDEX = {"G": 0, "D": 1, "B": 2, "?": 3}


def sheet_frames(name, w, h, count):
    """The frames of a sprite sheet (one row) as arcade textures."""
    sheet = arcade.load_spritesheet(os.path.join(ASSETS, name))
    return sheet.get_texture_grid((w, h), columns=count, count=count)


class Player(arcade.Sprite):
    def __init__(self, frames):
        super().__init__(frames[0])
        self.frames = frames
        self.clock_time = 0.0
        self.facing_left = False

    def animate(self, dt, on_ground):
        self.clock_time += dt
        if self.change_x < 0:
            self.facing_left = True
        elif self.change_x > 0:
            self.facing_left = False
        if not on_ground:
            frame = self.frames[6]
        elif self.change_x:
            frame = self.frames[2 + int(self.clock_time * 10) % 4]
        else:
            frame = self.frames[int(self.clock_time * 2) % 2]
        self.texture = frame.flip_left_right() if self.facing_left else frame


class Game(arcade.Window):
    def __init__(self):
        super().__init__(WIDTH, HEIGHT, "Arcplatformer")
        arcade.set_background_color((110, 193, 228))
        self.camera = arcade.Camera2D()
        self.ui = arcade.Camera2D()
        self.keys = set()
        self.score = 0
        self.coin_sound = arcade.load_sound(os.path.join(ASSETS, "coin.wav"))
        self.jump_sound = arcade.load_sound(os.path.join(ASSETS, "jump.wav"))
        self.tiles = arcade.load_spritesheet(os.path.join(ASSETS, "tiles.png")).get_texture_grid(
            (TILE, TILE), columns=8, count=8)
        self.coin_frames = sheet_frames("coin.png", 24, 24, 4)
        self.player_frames = sheet_frames("player.png", 32, 32, 7)
        self.score_text = arcade.Text("", 16, HEIGHT - 36, arcade.color.WHITE, 20)
        self.message_text = arcade.Text("", WIDTH / 2, HEIGHT / 2, arcade.color.WHITE, 22,
                                        anchor_x="center", anchor_y="center")
        self.setup()

    def setup(self):
        """Build the level from LEVEL (also R = restart)."""
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        self.coins = arcade.SpriteList()
        self.goal = arcade.SpriteList()
        self.player = Player(self.player_frames)
        rows = len(LEVEL)
        for r, line in enumerate(LEVEL):
            y = (rows - r - 1) * TILE + TILE / 2           # arcade: y goes up
            for c, ch in enumerate(line):
                x = c * TILE + TILE / 2
                if ch in TILE_INDEX:
                    self.walls.append(arcade.Sprite(self.tiles[TILE_INDEX[ch]], center_x=x, center_y=y))
                elif ch == "c":
                    coin = arcade.Sprite(self.coin_frames[0], center_x=x, center_y=y)
                    self.coins.append(coin)
                elif ch == "F":
                    self.goal.append(arcade.Sprite(os.path.join(ASSETS, "flag.png"), center_x=x, center_y=y + 16))
                elif ch == "P":
                    self.player.center_x, self.player.center_y = x, y
        self.level_width = max(len(line) for line in LEVEL) * TILE
        self.physics = arcade.PhysicsEnginePlatformer(self.player, walls=self.walls, gravity_constant=GRAVITY)
        self.clock_time = 0.0
        self.message = "Collect the coins and reach the flag!"
        self.message_until = 2.0
        self.won = False

    # ---------------------------------------------------------------- input
    def on_key_press(self, key, modifiers):
        self.keys.add(key)
        if key in (arcade.key.UP, arcade.key.W, arcade.key.SPACE) and self.physics.can_jump() and not self.won:
            self.player.change_y = JUMP
            arcade.play_sound(self.jump_sound)
        elif key == arcade.key.R:
            self.score = 0
            self.setup()
        elif key == arcade.key.ESCAPE:
            arcade.exit()

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    # ---------------------------------------------------------------- game loop
    def on_update(self, dt):
        self.clock_time += dt
        left = self.keys & {arcade.key.LEFT, arcade.key.A}
        right = self.keys & {arcade.key.RIGHT, arcade.key.D}
        self.player.change_x = 0 if self.won else (SPEED if right else 0) - (SPEED if left else 0)
        self.physics.update()
        self.player.left = max(0, self.player.left)
        self.player.animate(dt, self.physics.can_jump())
        for i, coin in enumerate(self.coins):
            coin.texture = self.coin_frames[int(self.clock_time * 8 + i) % 4]
        for coin in arcade.check_for_collision_with_list(self.player, self.coins):
            coin.remove_from_sprite_lists()
            self.score += 1
            arcade.play_sound(self.coin_sound)
        if not self.won and arcade.check_for_collision_with_list(self.player, self.goal):
            self.won = True
            self.message, self.message_until = f"You win! Score: {self.score}", self.clock_time + 3
        if self.player.top < -100:                         # fell into a hole
            self.setup()
        cx = min(max(self.player.center_x, WIDTH / 2), self.level_width - WIDTH / 2)
        self.camera.position = (cx, HEIGHT / 2)

    def on_draw(self):
        self.clear()
        with self.camera.activate():
            self.walls.draw()
            self.goal.draw()
            self.coins.draw()
            arcade.draw_sprite(self.player)
        with self.ui.activate():
            self.score_text.text = f"Score: {self.score}"
            self.score_text.draw()
            if self.clock_time < self.message_until:
                arcade.draw_lrbt_rectangle_filled(80, WIDTH - 80, HEIGHT / 2 - 28, HEIGHT / 2 + 28,
                                                  arcade.color.BLACK)
                self.message_text.text = self.message
                self.message_text.draw()


# ---------------------------------------------------------------- test hooks (RAD IDE)
def _test_hooks(window):
    """RADGAME_FRAMES / RADGAME_KEYS / RADGAME_SCREENSHOT: run a scripted, short game (tests)."""
    frames = int(os.environ.get("RADGAME_FRAMES") or 0)
    script = []
    for part in filter(None, os.environ.get("RADGAME_KEYS", "").split(",")):
        key, _, span = part.partition(":")
        a, _, b = span.partition("-")
        if a.isdigit() and b.isdigit():
            script.append((getattr(arcade.key, key.strip().upper(), 0), int(a), int(b)))
    if not frames and not script:
        return
    state = {"n": 0}
    update = window.on_update

    def on_update(dt):
        n = state["n"]
        for k, a, b in script:
            if n == a:
                window.on_key_press(k, 0)
            elif n == b:
                window.on_key_release(k, 0)
        update(1 / 60)
        state["n"] = n + 1
        if frames and state["n"] >= frames:
            shot = os.environ.get("RADGAME_SCREENSHOT")
            if shot:
                window.on_draw()
                arcade.get_image().save(shot)
            print(f"radgame-test: {state['n']} frames", flush=True)
            arcade.exit()
    window.on_update = on_update


def main():
    window = Game()
    _test_hooks(window)
    arcade.run()


if __name__ == "__main__":
    main()
