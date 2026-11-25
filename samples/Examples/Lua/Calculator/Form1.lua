-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Calculator - event handlers for Form1 (Lua, GUI Bridge).
-- Shows: many buttons sharing one function, a module (calc.lua), KeyPress (type 12*3 then Enter),
--        ListBox history (double-click reuses a result), menus, error handling with pcall + MsgBox.
local calc = require("calc")

local expr = ""          -- what the user typed so far
local just_done = false  -- the display shows a result: a digit starts a new expression

local function show()
  ui.txtDisplay.Text = (expr == "") and "0" or expr
end

local function press(key)
  if just_done and key:match("[%d%.%(]") then expr = "" end
  just_done = false
  expr = expr .. key
  show()
end

local function equals()
  if expr == "" then return end
  local ok, result = pcall(calc.evaluate, expr)
  if not ok then
    msgbox("Cannot calculate: " .. tostring(result):gsub("^.-:%d+: ", ""))
    return
  end
  local text = calc.format(result)
  ui.lblExpr.Caption = expr .. " ="
  ui.lstHistory:AddItem(expr .. " = " .. text)
  expr, just_done = text, true
  show()
end

function Form1_Load(e) show() end

-- digit / operator buttons (the IDE finds handlers by name, so each one is written out)
function cmd0_Click(e) press("0") end
function cmd1_Click(e) press("1") end
function cmd2_Click(e) press("2") end
function cmd3_Click(e) press("3") end
function cmd4_Click(e) press("4") end
function cmd5_Click(e) press("5") end
function cmd6_Click(e) press("6") end
function cmd7_Click(e) press("7") end
function cmd8_Click(e) press("8") end
function cmd9_Click(e) press("9") end
function cmdDot_Click(e) press(".") end
function cmdAdd_Click(e) press("+") end
function cmdSub_Click(e) press("-") end
function cmdMul_Click(e) press("*") end
function cmdDiv_Click(e) press("/") end

function cmdEq_Click(e) equals() end

function cmdClear_Click(e)
  expr, just_done = "", false
  ui.lblExpr.Caption = ""
  show()
end

function cmdBack_Click(e)
  expr = expr:sub(1, -2)
  show()
end

-- keyboard: the display is read-only, its KeyPress gets every key (e.args = "X Y Button KeyCode KeyChar")
-- KeyCode = the Windows key code (13 Enter, 8 Backspace, 27 Esc); the character (KeyChar) gives the rest
local KEYS = { ["13"] = "=", ["8"] = "back", ["27"] = "clear", Return = "=", BackSpace = "back", Escape = "clear",
  plus = "+", minus = "-", asterisk = "*", slash = "/", period = ".", parenleft = "(", parenright = ")" }
function txtDisplay_KeyPress(e)
  local keysym, ch = (e.args or ""):match("^%S+ %S+ %S+ (%S+) ?(%S*)")
  keysym, ch = keysym or "", ch or ""
  local k = KEYS[keysym] or (ch == "=" and "=") or (ch:match("^[%d%.%+%-%*/%(%)]$") and ch) or KEYS[ch]
  if k == "=" then equals()
  elseif k == "back" then cmdBack_Click()
  elseif k == "clear" then cmdClear_Click()
  elseif k then press(k) end
end

function lstHistory_DoubleClick(e)
  local line = ui.lstHistory.Text
  local value = line:match("= (.+)$")
  if value then expr, just_done = value, true; show() end
end

function mnuEditClear_Click(e) cmdClear_Click() end
function mnuEditClearHistory_Click(e) ui.lstHistory:Clear() end
function mnuHelpKeys_Click(e)
  msgbox("Click the display, then type: digits, + - * / ( ) . | Enter = result, Backspace, Esc = clear")
end
