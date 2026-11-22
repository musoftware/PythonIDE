# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Coin Collector - a small arcade-library game (https://api.arcade.academy).

Shows: an arcade.Window with on_draw / on_update / on_key_press, SpriteList + SpriteCircle sprites drawn in
code (no image files), collision lists (check_for_collision_with_list), a countdown timer, increasing
difficulty, a pause key, a high score kept in highscore.txt next to this file, and RAD IDE's test hooks
(RADGAME_FRAMES / RADGAME_KEYS / RADGAME_SCREENSHOT) so the IDE can play it for a few frames.

Arrow keys / WASD move, P pauses, R restarts, Esc quits.  Collect the gold coins, avoid the red meteors.
"""
import os
import random

import arcade

WIDTH, HEIGHT = 800, 600
TITLE = "Coin Collector"
PLAYER_SPEED = 320          # pixels per second
ROUND_SECONDS = 45
HERE = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(HERE, "highscore.txt")


def load_highscore() -> int:
    try:
        with open(HIGHSCORE_FILE, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_highscore(value: int) -> None:
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(value))
    except OSError:
        pass


class Game(arcade.Window):
    def __init__(self, seed=None):
        super().__init__(WIDTH, HEIGHT, TITLE)
        arcade.set_background_color(arcade.color.MIDNIGHT_BLUE)
        self.rng = random.Random(seed)
        self.keys = set()
        self.highscore = load_highscore()
        self.hud = arcade.Text("", 12, HEIGHT - 30, arcade.color.WHITE, 16)
        self.banner = arcade.Text("", WIDTH / 2, HEIGHT / 2, arcade.color.YELLOW, 28, anchor_x="center")
        self.setup()

    # ------------------------------------------------------------ game state
    def setup(self):
        self.player = arcade.SpriteCircle(16, arcade.color.SKY_BLUE)
        self.player.position = WIDTH / 2, HEIGHT / 2
        self.players = arcade.SpriteList()
        self.players.append(self.player)
        self.coins = arcade.SpriteList()
        self.meteors = arcade.SpriteList()
        starter = arcade.SpriteCircle(9, arcade.color.GOLD)    # a first coin right in front of the player
        starter.position = WIDTH / 2 + 90, HEIGHT / 2
        self.coins.append(starter)
        for _ in range(7):
            self.add_coin()
        for _ in range(3):
            self.add_meteor()
        self.score = 0
        self.time_left = ROUND_SECONDS
        self.paused = False
        self.over = False

    def add_coin(self):
        coin = arcade.SpriteCircle(9, arcade.color.GOLD)
        coin.position = self.rng.uniform(30, WIDTH - 30), self.rng.uniform(30, HEIGHT - 60)
        self.coins.append(coin)

    def add_meteor(self):
        m = arcade.SpriteCircle(14, arcade.color.RED_DEVIL)
        # start at an edge, fly across the screen
        m.position = self.rng.choice([(-20, self.rng.uniform(0, HEIGHT)), (WIDTH + 20, self.rng.uniform(0, HEIGHT))])
        m.change_x = self.rng.uniform(90, 170) * (1 if m.center_x < 0 else -1)
        m.change_y = self.rng.uniform(-80, 80)
        self.meteors.append(m)

    def finish(self, why: str):
        self.over = True
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.score)
        self.banner.text = f"{why}  -  score {self.score}  (R = play again)"
        print(f"GAMEOVER {why} score={self.score} high={self.highscore}", flush=True)

    # ------------------------------------------------------------ input
    def on_key_press(self, key, modifiers):
        self.keys.add(key)
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key == arcade.key.P and not self.over:
            self.paused = not self.paused
            print("PAUSE" if self.paused else "RESUME", flush=True)
        elif key == arcade.key.R:
            self.setup()
            print("RESTART", flush=True)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    # ------------------------------------------------------------ frame
    def on_update(self, dt):
        if self.paused or self.over:
            return
        k = self.keys
        dx = (arcade.key.RIGHT in k or arcade.key.D in k) - (arcade.key.LEFT in k or arcade.key.A in k)
        dy = (arcade.key.UP in k or arcade.key.W in k) - (arcade.key.DOWN in k or arcade.key.S in k)
        self.player.center_x = min(max(self.player.center_x + dx * PLAYER_SPEED * dt, 16), WIDTH - 16)
        self.player.center_y = min(max(self.player.center_y + dy * PLAYER_SPEED * dt, 16), HEIGHT - 46)
        for m in self.meteors:          # change_x/y are pixels per second here
            m.center_x += m.change_x * dt
            m.center_y += m.change_y * dt
            if not (-40 < m.center_x < WIDTH + 40) or not (-40 < m.center_y < HEIGHT + 40):
                m.remove_from_sprite_lists()
                self.add_meteor()
        for coin in arcade.check_for_collision_with_list(self.player, self.coins):
            coin.remove_from_sprite_lists()
            self.score += 1
            print(f"COIN score={self.score}", flush=True)
            self.add_coin()
            if self.score % 5 == 0:     # harder every 5 coins
                self.add_meteor()
        if arcade.check_for_collision_with_list(self.player, self.meteors):
            self.finish("Hit by a meteor")
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.finish("Time is up")

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, WIDTH, HEIGHT - 40, HEIGHT, arcade.color.DARK_SLATE_GRAY)
        self.coins.draw()
        self.meteors.draw()
        self.players.draw()
        self.hud.text = (f"Score {self.score}    High {self.highscore}    Time {max(0, self.time_left):4.1f}"
                         + ("    PAUSED" if self.paused else ""))
        self.hud.draw()
        if self.over:
            self.banner.draw()


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
    seed = os.environ.get("COIN_SEED")           # fixed coin positions for repeatable tests
    window = Game(int(seed) if seed else None)
    _test_hooks(window)
    arcade.run()


if __name__ == "__main__":
    main()
