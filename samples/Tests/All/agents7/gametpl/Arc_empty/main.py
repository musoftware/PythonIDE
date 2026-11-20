"""Arcempty - an arcade window (https://api.arcade.academy). Arrow keys move the ball, Esc quits."""
import os

import arcade

WIDTH, HEIGHT = 800, 600
SPEED = 300          # pixels per second


class Game(arcade.Window):
    def __init__(self):
        super().__init__(WIDTH, HEIGHT, "Arcempty")
        arcade.set_background_color(arcade.color.DARK_SLATE_BLUE)
        self.x, self.y = WIDTH / 2, HEIGHT / 2
        self.keys = set()
        self.help = arcade.Text("Arrow keys move the ball", 16, HEIGHT - 32, arcade.color.WHITE, 16)

    def on_key_press(self, key, modifiers):
        self.keys.add(key)
        if key == arcade.key.ESCAPE:
            arcade.exit()

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_update(self, dt):
        dx = (arcade.key.RIGHT in self.keys) - (arcade.key.LEFT in self.keys)
        dy = (arcade.key.UP in self.keys) - (arcade.key.DOWN in self.keys)
        self.x = min(max(self.x + dx * SPEED * dt, 20), WIDTH - 20)
        self.y = min(max(self.y + dy * SPEED * dt, 20), HEIGHT - 20)

    def on_draw(self):
        self.clear()
        arcade.draw_circle_filled(self.x, self.y, 20, arcade.color.ORANGE)
        self.help.draw()


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
