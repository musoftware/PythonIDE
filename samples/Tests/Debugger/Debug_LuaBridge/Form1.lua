-- Debugger test (Lua): breakpoint on the "local text = ..." line of cmdGreet_Click, then F5 and Greet.
local clicks = 0

local function make_greeting(name, n)
  local text = "Hello, " .. name .. "! (click " .. n .. ")"
  return text
end

function Form1_Load(e)
  rad.set("lblOut", "Caption", "Press Greet.")
end

function cmdGreet_Click(e)
  local name = rad.get("txtName", "Text")
  clicks = clicks + 1
  local info = { name = name, clicks = clicks, tags = { "a", "b" } }
  local text = make_greeting(name, clicks)
  rad.set("lblOut", "Caption", text)
end
