-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Module notestore - the notes of the app, saved as UTF-8 text in notes.txt:
--   one note per block: "# <title>" line, then the body lines, then a line with a single "."
-- Also: multi-line TextBox access over the GUI Bridge ("ESC" commands escape \ newline and CR).
local M = {}
M.FILE = "notes.txt"
M.notes = {}      -- { {title=..., body=...}, ... }

function M.load()
  M.notes = {}
  local f = io.open(M.FILE, "r")
  if not f then return 0 end
  local cur
  for line in f:lines() do
    line = line:gsub("\r$", "")
    if not cur and line:sub(1, 2) == "# " then
      cur = { title = line:sub(3), body = {} }
    elseif cur and line == "." then
      cur.body = table.concat(cur.body, "\n")
      M.notes[#M.notes + 1] = cur
      cur = nil
    elseif cur then
      cur.body[#cur.body + 1] = (line:gsub("^%.%.", "."))   -- a body line "." is stored as ".."
    end
  end
  f:close()
  return #M.notes
end

function M.save()
  local f = assert(io.open(M.FILE, "w"))
  for _, n in ipairs(M.notes) do
    f:write("# ", n.title, "\n")
    for line in (n.body .. "\n"):gmatch("(.-)\n") do
      f:write(line == "." and ".." or line, "\n")
    end
    f:write(".\n")
  end
  f:close()
end

-- index of the first note whose title (or body) contains text, from position start; nil if none
function M.find(text, titles_only, start)
  text = text:lower()
  for i = start or 1, #M.notes do
    local n = M.notes[i]
    if n.title:lower():find(text, 1, true) or (not titles_only and n.body:lower():find(text, 1, true)) then
      return i
    end
  end
  return nil
end

-- ---------------------------------------------------------------- multi-line text over the bridge
local function esc(s) return (s:gsub("\\", "\\\\"):gsub("\r?\n", "\\n")) end
local function unesc(s)
  return (s:gsub("\\(.)", function(c) return c == "n" and "\n" or c == "r" and "\r" or c end))
end

-- In a native exe (Build > Publish, radforms) rad.get / rad.set call the form directly and keep newlines;
-- under the IDE's GUI Bridge the values travel one line at a time, so "ESC" commands are used there.
local NATIVE = rawget(_G, "_RADNATIVE") ~= nil

function M.get_text(obj)
  if NATIVE then return (rad.get(obj, "Text"):gsub("\r\n", "\n")) end
  io.stdout:write("ESC GET ", obj, " Text\n")
  io.stdout:flush()
  local line = io.stdin:read("*l") or ""
  return (unesc(line:gsub("\r$", "")):gsub("\r\n", "\n"))
end

function M.set_text(obj, value)
  if NATIVE then rad.set(obj, "Text", (value:gsub("\r?\n", "\r\n"))); return end
  io.stdout:write("ESC SET ", obj, " Text ", esc(value), "\n")
  io.stdout:flush()
end

return M
