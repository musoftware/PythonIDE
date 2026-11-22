-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Guess the Number - event handlers for Form1 (Lua, GUI Bridge).
-- Shows: a game loop driven by events, a Timer (seconds), ProgressBar (tries left), menus to pick a level,
--        KeyPress (Enter = guess), MsgBox, best scores saved to a file by a module (scores.lua).
local scores = require("scores")

local LEVELS = { Easy = { max = 50, tries = 8 }, Normal = { max = 100, tries = 10 }, Hard = { max = 1000, tries = 12 } }
local level = "Normal"
local secret, tries, seconds, playing = 0, 0, 0, false
local best = {}

-- the test (and curious players) can fix the secret number: RADEX_SECRET=42
local function pick_secret(max)
  local fixed = tonumber(os.getenv("RADEX_SECRET") or "")
  if fixed then return fixed end
  return math.random(1, max)
end

local function show_best()
  local b = best[level]
  ui.lblBest.Caption = b and string.format("Best: %d tries, %d s", b.tries, b.secs) or "Best: -"
end

local function new_game()
  local L = LEVELS[level]
  secret, tries, seconds, playing = pick_secret(L.max), 0, 0, true
  ui.lblTitle.Caption = string.format("I am thinking of a number from 1 to %d (%s)", L.max, level)
  ui.lblHint.Caption = string.format("You have %d tries. Good luck!", L.tries)
  ui.prgTries.Maximum = L.tries
  ui.prgTries.Value = 0
  ui.lblTime.Caption = "Time: 0 s"
  ui.lstHistory:Clear()
  ui.txtGuess.Text = ""
  ui.tmrClock.Enabled = "True"
  show_best()
end

local function finish(won)
  playing = false
  ui.tmrClock.Enabled = "False"
  if won then
    local text = string.format("Correct! %d is the number - %d tries in %d seconds.", secret, tries, seconds)
    if scores.is_better(best[level], tries, seconds) then
      best[level] = { tries = tries, secs = seconds }
      scores.save(best)
      text = text .. " New best score!"
    end
    ui.lblHint.Caption = "You won!"
    show_best()
    msgbox(text)
  else
    ui.lblHint.Caption = "Out of tries - the number was " .. secret
    msgbox("Game over. The number was " .. secret .. ". Game > New game to play again.")
  end
end

function Form1_Load(e)
  math.randomseed(os.time())
  best = scores.load()
  new_game()
end

function cmdGuess_Click(e)
  if not playing then return end
  local n = tonumber(ui.txtGuess.Text)
  local L = LEVELS[level]
  if not n or n < 1 or n > L.max or n ~= math.floor(n) then
    ui.lblHint.Caption = "Type a whole number from 1 to " .. L.max
    return
  end
  tries = tries + 1
  ui.prgTries.Value = tries
  ui.txtGuess.Text = ""
  if n == secret then
    ui.lstHistory:AddItem(string.format("%2d. %d  correct!", tries, n))
    finish(true)
  else
    local hint = n < secret and "higher" or "lower"
    ui.lstHistory:AddItem(string.format("%2d. %d  -> try %s", tries, n, hint))
    ui.lblHint.Caption = string.format("%d is wrong - go %s (%d tries left)", n, hint, L.tries - tries)
    if tries >= L.tries then finish(false) end
  end
end

function txtGuess_KeyPress(e)
  if (e.args or ""):find("Return") then cmdGuess_Click(e) end
end

function tmrClock_Tick(e)
  if not playing then return end
  seconds = seconds + 1
  ui.lblTime.Caption = "Time: " .. seconds .. " s"
end

function mnuGameNew_Click(e) new_game() end
function mnuGameExit_Click(e) rad.quit() end
function mnuLevelEasy_Click(e) level = "Easy"; new_game() end
function mnuLevelNormal_Click(e) level = "Normal"; new_game() end
function mnuLevelHard_Click(e) level = "Hard"; new_game() end
