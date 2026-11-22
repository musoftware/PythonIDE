-- Event handlers for Form1 - written for the GUI Bridge (rad.lua); the native build embeds Lua 5.4 and
-- runs the same code against radforms. Handlers: global functions <Control>_<Event>(e).
local Helpers = require("Helpers")

local ticks = 0

function Form1_Load(e)
  rad.set("lblOut", "Caption", "ready")
  ui.lstLog:AddItem("Form1 loaded")
end

function cmdAdd_Click(e)
  local a = rad.getnum("txtA", "Text")
  local b = rad.getnum("txtB", "Text")
  rad.set("lblOut", "Caption", math.tointeger(a + b) or (a + b))
  -- Helpers.lua is a module of this project (require): embedded in the exe
  rad.call("lstLog", "AddItem", string.format("%g x %g = %g", a, b, Helpers.multiply(a, b)))
end

function txtA_TextChanged(e)
  ui.lblEcho.Caption = ui.txtA.Text
end

function chkBig_CheckedChanged(e)
  if rad.getnum("chkBig", "Value") == 1 then
    rad.set("lblOut", "FontSize", 14)
    rad.set("lblOut", "Caption", "big")
  else
    rad.set("lblOut", "FontSize", 9)
    rad.set("lblOut", "Caption", "small")
  end
end

function optTwo_CheckedChanged(e)
  rad.set("lblEcho", "Caption", rad.get("optTwo", "Value"))
end

function cboColor_SelectedIndexChanged(e)
  rad.set("lblOut", "Caption", rad.get("cboColor", "Text"))
end

function tmrTick_Tick(e)
  ticks = ticks + 1
  rad.set("lblTicks", "Caption", ticks)
  rad.set("prgTicks", "Value", ticks % 51)
end

function cmdShow2_Click(e) rad.show("Form2") end

function mnuForm2_Click(e) rad.show("Form2") end

function mnuAbout_Click(e) msgbox("RAD IDE native Lua demo") end

function mnuExit_Click(e) rad.quit() end

function cmdMsg_Click(e)
  rad.msgbox("Hello from radforms")
  rad.set("lblOut", "Caption", "msg done")
end

function cmdArabic_Click(e)
  rad.set("lblOut", "Caption", "مرحبا بالعالم")
end
