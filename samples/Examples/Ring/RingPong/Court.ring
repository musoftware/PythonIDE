# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Ring Pong - the code of scene Court (RingRayLib game made with the RAD IDE scene designer).
# Shows: scene objects as globals (Player, Cpu, Ball, ScoreText), the keyboard_move behaviour (Player),
# a frame handler (Scene_Update dt) with our own ball physics and paddle collisions, a simple computer
# player, keyboard events, ShowMessage, and a timer that serves the ball again.

nPlayer = 0             # points of the player (left)
nCpu = 0                # points of the computer (right)
nSpeed = 300            # ball speed, grows with every hit
nVx = 0  nVy = 0        # ball velocity (pixels / second)
lServing = false        # waiting for the serve timer
nWinScore = 5

# the scene starts
func Scene_Load
    ShowMessage("Ring Pong - first to " + nWinScore, 2)
    Serve(1)

# every frame (dt = seconds since the last frame)
func Scene_Update dt
    if lServing return ok
    Ball.x += nVx * dt
    Ball.y += nVy * dt
    # top / bottom walls
    if Ball.y < 0
        Ball.y = 0  nVy = fabs(nVy)
    but Ball.y + Ball.h > 480
        Ball.y = 480 - Ball.h  nVy = -fabs(nVy)
    ok
    # paddles: bounce back and add spin from where the ball hit the paddle
    if nVx < 0 and Hit(Player)
        Ball.x = Player.x + Player.w
        Bounce(Player, 1)
    but nVx > 0 and Hit(Cpu)
        Ball.x = Cpu.x - Ball.w
        Bounce(Cpu, -1)
    ok
    # the computer follows the ball (a little slower than the ball, so it can be beaten)
    nTarget = Ball.y + Ball.h / 2 - Cpu.h / 2
    nStep = 250 * dt
    if Cpu.y < nTarget - nStep Cpu.y += nStep but Cpu.y > nTarget + nStep Cpu.y -= nStep ok
    if Cpu.y < 0 Cpu.y = 0 ok
    if Cpu.y + Cpu.h > 480 Cpu.y = 480 - Cpu.h ok
    # a point is scored when the ball leaves the court
    if Ball.x + Ball.w < 0
        nCpu++
        Point(-1)
    but Ball.x > 800
        nPlayer++
        Point(1)
    ok

# a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown key
    if key = "escape" Quit() ok
    if key = "r"
        nPlayer = 0  nCpu = 0
        ScoreText.text = "0 : 0"
        Serve(1)
    ok

# the serve timer (AddTimer("ServeTimer", ms)) fires once
func ServeTimer_Tick
    StopTimer("ServeTimer")
    lServing = false

# ---------------------------------------------------------------- helpers
func Hit oPaddle
    return Ball.x < oPaddle.x + oPaddle.w and Ball.x + Ball.w > oPaddle.x and
           Ball.y < oPaddle.y + oPaddle.h and Ball.y + Ball.h > oPaddle.y

func Bounce oPaddle, nDir
    nOffset = (Ball.y + Ball.h / 2 - (oPaddle.y + oPaddle.h / 2)) / (oPaddle.h / 2)    # -1 .. 1
    nSpeed = min(nSpeed + 25, 700)
    nVx = nDir * nSpeed
    nVy = nOffset * nSpeed * 0.75
    see "hit " + oPaddle.name + nl

func Point nDir
    ScoreText.text = "" + nPlayer + " : " + nCpu
    see "score " + nPlayer + ":" + nCpu + nl
    if nPlayer >= nWinScore or nCpu >= nWinScore
        if nPlayer > nCpu ShowMessage("You win!", 3) else ShowMessage("The computer wins!", 3) ok
        nPlayer = 0  nCpu = 0
    ok
    Serve(nDir)

func Serve nDir
    Ball.x = 400 - Ball.w / 2
    Ball.y = 240 - Ball.h / 2
    nSpeed = 300
    nVx = nDir * nSpeed
    nVy = 120
    lServing = true
    AddTimer("ServeTimer", 700)
