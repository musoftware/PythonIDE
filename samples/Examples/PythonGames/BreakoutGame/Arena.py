# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Arena - the Breakout game code (pygame through RAD IDE's radgame runtime).

Shows: keyboard input (IsKeyDown / Scene_KeyDown), a per-frame update loop with dt, collision tests
(obj.overlaps), destroying objects, score + lives in UI text objects ({score} / {lives} / {best}),
saved best score (SaveData / LoadData -> savegame.json), on-screen messages and restarting the scene.

Keys: Left/Right (or A/D) move the paddle, Space launches the ball, Escape quits.
"""
import math

from radgame import *  # noqa: F401,F403 - the game helpers
from Arena_designer import *  # noqa: F401,F403 - Paddle, Ball, Brick1..Brick50, ScoreText ...

PADDLE_SPEED = 520          # pixels per second
BALL_SPEED = 380
ball = {"vx": 0.0, "vy": 0.0, "launched": False}


def stick_ball():
    """Put the ball on the paddle until Space is pressed."""
    ball["launched"] = False
    Ball.x = Paddle.x + Paddle.width / 2 - Ball.width / 2
    Ball.y = Paddle.y - Ball.height - 2


def launch():
    ball["launched"] = True
    ball["vx"], ball["vy"] = BALL_SPEED * 0.6, -BALL_SPEED * 0.8
    print("LAUNCH", flush=True)


# the scene: the scene starts
def Scene_Load():
    if game.vars.get("new_game", True):
        game.score, game.lives = 0, 3
    game.vars["new_game"] = True
    game.vars["best"] = LoadData("best", 0)
    stick_ball()
    ShowMessage("Space = launch    Left / Right = move", 2.5)


# the scene: a key goes down
def Scene_KeyDown(key):
    if key == "space" and not ball["launched"]:
        launch()
    elif key == "escape":
        Quit()


# the scene: every frame (dt = seconds since the last frame)
def Scene_Update(dt):
    # --- paddle
    if IsKeyDown("left"):
        Paddle.x -= PADDLE_SPEED * dt
    if IsKeyDown("right"):
        Paddle.x += PADDLE_SPEED * dt
    Paddle.x = max(0, min(800 - Paddle.width, Paddle.x))
    if not ball["launched"]:
        stick_ball()
        return
    # --- ball movement and walls
    Ball.x += ball["vx"] * dt
    Ball.y += ball["vy"] * dt
    if Ball.x <= 0 or Ball.right >= 800:
        ball["vx"] = -ball["vx"]
        Ball.x = max(0, min(800 - Ball.width, Ball.x))
    if Ball.y <= 40:
        ball["vy"] = abs(ball["vy"])
    # --- paddle: the bounce angle depends on where the ball hits it
    if ball["vy"] > 0 and Ball.overlaps(Paddle):
        offset = (Ball.center[0] - Paddle.center[0]) / (Paddle.width / 2)      # -1 .. 1
        angle = math.radians(90 - 60 * max(-1.0, min(1.0, offset)))
        ball["vx"], ball["vy"] = BALL_SPEED * math.cos(angle), -BALL_SPEED * math.sin(angle)
        Ball.y = Paddle.y - Ball.height
    # --- bricks
    for brick in FindGroup("Brick"):
        if Ball.overlaps(brick):
            brick.destroy()
            ball["vy"] = -ball["vy"]
            AddScore(int(brick.props.get("points", 10)))
            left = len(FindGroup("Brick"))
            print(f"HIT {brick.name} score={game.score} left={left}", flush=True)
            if left == 0:
                game_over("You win!")
            break
    # --- missed the ball
    if Ball.y > 600:
        game.lives -= 1
        print(f"MISS lives={game.lives}", flush=True)
        if game.lives <= 0:
            game_over("Game over")
        else:
            stick_ball()


def game_over(text):
    best = max(game.score, LoadData("best", 0))
    SaveData("best", best)
    print(f"GAMEOVER {text} score={game.score} best={best}", flush=True)
    ShowMessage(f"{text}  Score {game.score}", 3)
    game.vars["new_game"] = True
    RestartScene()
