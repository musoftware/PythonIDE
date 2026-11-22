-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Notes - event handlers for Form1 (Lua, GUI Bridge).
-- Shows: a list + editor app, a multi-line TextBox, saving to a UTF-8 text file (Arabic text works),
--        a modal Find dialog (FindForm, CALL ShowDialog), menus, StatusBar, a data module (notestore.lua).
store = require("notestore")      -- global: FindForm.lua uses it too (all forms share one Lua state)

local current = 0                 -- index of the note in the editor (0 = a new, unsaved note)

local function status(text) ui.sbStatus.Text = text end

function refresh_list(select)
  ui.lstNotes:Clear()
  for _, n in ipairs(store.notes) do ui.lstNotes:AddItem(n.title) end
  ui.lblCount.Caption = #store.notes .. " notes"
  if select and select > 0 then ui.lstNotes.ListIndex = select - 1 end
end

function open_note(i)
  local n = store.notes[i]
  if not n then return end
  current = i
  ui.txtTitle.Text = n.title
  store.set_text("txtBody", n.body)
  status("Note " .. i .. " of " .. #store.notes)
end

function Form1_Load(e)
  local count = store.load()
  if count == 0 then        -- first run: two example notes (one in Arabic)
    store.notes = {
      { title = "Welcome", body = "Notes is a RAD IDE example written in Lua.\nSelect a note, edit it and press Save." },
      { title = "ملاحظة عربية", body = "هذا نص عربي يُحفظ في ملف UTF-8.\nيدعم المحرر الكتابة من اليمين إلى اليسار." },
    }
    store.save()
  end
  refresh_list(1)
  open_note(1)
end

function lstNotes_SelectedIndexChanged(e)
  local i = tonumber(ui.lstNotes.ListIndex) or -1
  if i >= 0 and i + 1 ~= current then open_note(i + 1) end
end

function cmdNew_Click(e)
  current = 0
  ui.txtTitle.Text = ""
  store.set_text("txtBody", "")
  ui.txtTitle:SetFocus()
  status("New note - type a title and press Save")
end

function cmdSave_Click(e)
  local title = ui.txtTitle.Text:gsub("^%s+", ""):gsub("%s+$", "")
  if title == "" then
    msgbox("Please type a title for the note.")
    return
  end
  local body = store.get_text("txtBody")
  if current == 0 then
    store.notes[#store.notes + 1] = { title = title, body = body }
    current = #store.notes
  else
    store.notes[current] = { title = title, body = body }
  end
  store.save()
  refresh_list(current)
  status("Saved '" .. title .. "' to " .. store.FILE)
end

function cmdDelete_Click(e)
  if current == 0 then return end
  local title = store.notes[current].title
  if rad.input("Type YES to delete '" .. title .. "'") ~= "YES" then return end
  table.remove(store.notes, current)
  store.save()
  current = 0
  refresh_list()
  if #store.notes > 0 then open_note(1); ui.lstNotes.ListIndex = 0 else cmdNew_Click() end
  status("Deleted '" .. title .. "'")
end

function mnuFileNew_Click(e) cmdNew_Click(e) end
function mnuFileSave_Click(e) cmdSave_Click(e) end
function mnuFileDelete_Click(e) cmdDelete_Click(e) end
function mnuFileExit_Click(e) rad.quit() end

-- Edit > Find...: a modal dialog; its Find button (FindForm.lua) does the search
function mnuEditFind_Click(e)
  rad.call("FindForm", "ShowDialog")
end
