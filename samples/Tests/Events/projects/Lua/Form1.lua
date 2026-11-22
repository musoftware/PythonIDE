-- EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
local closing = 0

local function evlog(name, rest)
  local p = os.getenv("RADEVT_LOG")
  if not p or p == "" then return end
  local f = io.open(p, "ab")
  if not f then return end
  f:write("EVT " .. name .. ((rest and rest ~= "") and (" " .. rest) or "") .. "\n")
  f:close()
end

function Form1_Load(e)
  evlog("Form1_Load", "")
end

function Form1_Activated(e)
  evlog("Form1_Activated", "")
end

function Form1_FormClosed(e)
  evlog("Form1_FormClosed", "")
end

function cmdA_MouseDown(e)
  evlog("cmdA_MouseDown", e and e.args or "")
end

function cmdA_MouseUp(e)
  evlog("cmdA_MouseUp", e and e.args or "")
end

function cmdA_Click(e)
  evlog("cmdA_Click", "")
end

function lblA_MouseDown(e)
  evlog("lblA_MouseDown", e and e.args or "")
end

function lblA_MouseUp(e)
  evlog("lblA_MouseUp", e and e.args or "")
end

function lblA_Click(e)
  evlog("lblA_Click", "")
end

function txtA_GotFocus(e)
  evlog("txtA_GotFocus", "")
end

function txtA_LostFocus(e)
  evlog("txtA_LostFocus", "")
end

function txtA_KeyDown(e)
  evlog("txtA_KeyDown", e and e.args or "")
end

function txtA_KeyPress(e)
  evlog("txtA_KeyPress", e and e.args or "")
end

function txtA_KeyUp(e)
  evlog("txtA_KeyUp", e and e.args or "")
end

function txtA_TextChanged(e)
  evlog("txtA_TextChanged", "text=" .. rad.get("txtA", "Text"))
end

function txtB_GotFocus(e)
  evlog("txtB_GotFocus", "")
end

function txtB_LostFocus(e)
  evlog("txtB_LostFocus", "")
end

function chkA_CheckedChanged(e)
  evlog("chkA_CheckedChanged", "value=" .. rad.get("chkA", "Value"))
end

function lstA_SelectedIndexChanged(e)
  evlog("lstA_SelectedIndexChanged", "index=" .. rad.get("lstA", "ListIndex"))
end

function Form1_FormClosing(e)
  closing = closing + 1
  evlog("Form1_FormClosing", "")
  if closing == 1 then rad.set("Form1", "Cancel", "True") end
end

function cmdCode_Click(e)
  evlog("cmdCode_Click", "begin")
  rad.set("txtA", "Text", "code")
  rad.set("chkA", "Value", 1)
  rad.set("lstA", "ListIndex", 2)
  evlog("cmdCode_Click", "end")
end

function cmdTmr_Click(e)
  evlog("cmdTmr_Click", "")
  rad.set("tmrA", "Enabled", "True")
end

function tmrA_Tick(e)
  rad.set("tmrA", "Enabled", "False")
  evlog("tmrA_Tick", "")
end
