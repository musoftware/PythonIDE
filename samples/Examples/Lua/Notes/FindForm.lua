-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- FindForm - the modal Find dialog of Notes. ShowDialog answers at once (the program keeps running), so
-- the result is handled here, in the dialog's own OK / Cancel handlers.
local last = 0       -- the note found last time: Find again continues after it

function FindForm_Load(e)
  rad.call("FindForm.txtFind", "SetFocus")
end

function cmdOK_Click(e)
  local text = rad.get("FindForm.txtFind", "Text")
  if text == "" then return end
  local titles = rad.get("FindForm.chkTitles", "Value") == "1"
  local i = store.find(text, titles, last + 1) or store.find(text, titles, 1)
  if not i then
    msgbox("'" .. text .. "' was not found.")
    return
  end
  last = i
  rad.hide("FindForm")
  rad.set("Form1.lstNotes", "ListIndex", i - 1)
  open_note(i)
  rad.set("Form1.sbStatus", "Text", "Found '" .. text .. "' in note " .. i)
end

function cmdCancel_Click(e)
  rad.hide("FindForm")
end

function txtFind_KeyPress(e)
  if (e.args or ""):match("^%S+ %S+ %S+ 13") or (e.args or ""):find("Return") then cmdOK_Click(e) end
end
