-- RAD IDE - GUI Bridge client for Lua 5.1-5.4 / LuaJIT (copied into the project when it runs).
--
-- The IDE draws the forms; this program talks to it over stdin/stdout
-- (protocol: docs/CONTRACTS.md section 1). Everything is synchronous.
--
--   rad.set(obj, prop, value)          set a property     rad.set("lblOut", "Caption", "Hi")
--   rad.get(obj, prop)       -> string read a property    rad.get("txtA", "Text")
--   rad.getnum(obj, prop)    -> number read a property as a number
--   rad.call(obj, method, ...)         call a method      rad.call("lstLog", "AddItem", "line")
--   rad.msgbox(text) / msgbox(text)    message box (waits for OK)
--   rad.input(prompt)        -> string input box
--   rad.show(form) / rad.hide(form)    show or hide a form
--   rad.quit()                         quit the program ("end" is a Lua keyword)
--   ui.txtA.Text, ui.lblOut.Caption = "x", ui.lstLog:AddItem("x")   property / method sugar
--   radcall("Module.func", ...) -> value
--        call a function of any project module, in any language, through the RAD Hub
--        (arguments and the result are JSON values; JSON null is rad.null).
--        Uses LuaSocket when installed (luarocks install luasocket), otherwise a small
--        Python helper (radcall_helper.py) for each call.
-- Handlers are global functions named <Control>_<Event>; they get one table
--   e = { X, Y, Button, KeyCode, KeyChar, args }   (mouse/key events, zeros otherwise)
local rad = {}
rad.worker = false        -- true inside a RAD Hub worker: no IDE on stdin/stdout
rad.null = setmetatable({}, { __tostring = function() return "null" end })

-- folder of this file (radcall_helper.py and reference proxies live next to it)
local SRC = debug and debug.getinfo and debug.getinfo(1, "S").source or ""
local HERE = SRC:sub(1, 1) == "@" and SRC:sub(2):match("^(.*)[/\\][^/\\]*$") or "."

-- require("MathLib.ref") loads the reference proxy MathLib.ref.lua (Add Reference in the IDE):
-- the standard searcher would look for MathLib/ref.lua
local function ref_searcher(name)
  if not name:match("%.ref$") then return nil end
  local tried = {}
  for _, dir in ipairs({ ".", HERE }) do
    local file = dir .. "/" .. name .. ".lua"
    local f = io.open(file, "r")
    if f then
      f:close()
      local chunk, e = loadfile(file)
      if not chunk then error(e, 0) end
      return chunk, file
    end
    tried[#tried + 1] = "\n\tno file '" .. file .. "'"
  end
  return table.concat(tried)
end
table.insert(package.searchers or package.loaders, 2, ref_searcher)

io.stdout:setvbuf("no")
io.stderr:setvbuf("no")

local function clean(v)
  if v == nil then return "" end
  return (tostring(v):gsub("\r?\n", " "))
end

local function send(line)
  if rad.worker then
    io.stderr:write(line, "\n")
  else
    io.stdout:write(line, "\n")
    io.stdout:flush()
  end
end

local function read_line()
  if rad.worker then return "" end
  local line = io.stdin:read("*l")
  if line == nil then os.exit(0) end      -- the IDE went away
  return (line:gsub("\r$", ""))
end

-- "ESC <command>" (radide/runtimes/bridge.py): \ newline CR escaped in the values, so multi-line text survives
local function esc(v)
  if v == nil then return "" end
  return (tostring(v):gsub("\\", "\\\\"):gsub("\n", "\\n"):gsub("\r", "\\r"))
end

local function unesc(s)
  return (s:gsub("\\(.)", function(c)
    if c == "n" then return "\n" elseif c == "r" then return "\r" elseif c == "\\" then return "\\" end
    return "\\" .. c
  end))
end

function rad.set(obj, prop, value)
  local s = value == nil and "" or tostring(value)
  if s:find("[\r\n]") then
    send("ESC SET " .. obj .. " " .. prop .. " " .. esc(s))     -- multi-line text
  else
    send("SET " .. obj .. " " .. prop .. " " .. s)
  end
end

function rad.get(obj, prop)
  send("ESC GET " .. obj .. " " .. prop)
  return unesc(read_line())
end

function rad.getnum(obj, prop)
  return tonumber((rad.get(obj, prop):match("^%s*([-+]?[%d%.]+[eE]?[-+]?%d*)"))) or 0
end

function rad.call(obj, method, ...)
  local n, parts = select("#", ...), {}
  for i = 1, n do parts[i] = clean((select(i, ...))) end
  local line = "CALL " .. obj .. " " .. method
  if n > 0 then line = line .. " " .. table.concat(parts, "\t") end
  send(line)
  return read_line()
end

function rad.msgbox(text)
  send("MSGBOX " .. clean(text))
  return read_line()
end

function rad.input(prompt)
  send("INPUT " .. clean(prompt))
  return read_line()
end

function rad.show(form) send("SHOW " .. form) end
function rad.hide(form) send("HIDE " .. form) end

function rad.quit()
  send("END")
  os.exit(0)
end
rad["end"] = rad.quit

-- ------------------------------------------------------------------ ui sugar
local METHODS = { additem = true, removeitem = true, clear = true, list = true, setfocus = true,
  move = true, refresh = true, zorder = true, showdialog = true, show = true, hide = true,
  start = true, stop = true }

local function control(name)
  return setmetatable({}, {
    __index = function(self, key)
      if METHODS[key:lower()] then
        return function(selfarg, ...)
          if selfarg == self then return rad.call(name, key, ...) end
          return rad.call(name, key, selfarg, ...)      -- called with "." instead of ":"
        end
      end
      return rad.get(name, key)
    end,
    __newindex = function(_, key, value) rad.set(name, key, value) end,
  })
end
rad.ui = setmetatable({}, { __index = function(_, name) return control(name) end })

-- ------------------------------------------------------------------ JSON
local json = {}
rad.json = json

local function utf8char(cp)
  if cp < 0x80 then return string.char(cp) end
  if cp < 0x800 then return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40) end
  if cp < 0x10000 then
    return string.char(0xE0 + math.floor(cp / 0x1000), 0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
  end
  return string.char(0xF0 + math.floor(cp / 0x40000), 0x80 + math.floor(cp / 0x1000) % 0x40,
    0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
end

local ESC = { ['"'] = '\\"', ["\\"] = "\\\\", ["\b"] = "\\b", ["\f"] = "\\f", ["\n"] = "\\n",
  ["\r"] = "\\r", ["\t"] = "\\t" }

local function is_array(t)
  local n = 0
  for k in pairs(t) do
    if type(k) ~= "number" or k < 1 or k % 1 ~= 0 then return false end
    n = n + 1
  end
  for i = 1, n do if t[i] == nil then return false end end
  return true, n
end

function json.encode(v, seen)
  local t = type(v)
  if v == nil or v == rad.null then return "null" end
  if t == "boolean" then return tostring(v) end
  if t == "number" then
    if v ~= v or v == math.huge or v == -math.huge then return "null" end
    if v % 1 == 0 and v > -1e15 and v < 1e15 then return string.format("%d", v) end
    return string.format("%.17g", v)
  end
  if t == "string" then
    return '"' .. v:gsub('[%c"\\]', function(c)
      return ESC[c] or string.format("\\u%04x", c:byte())
    end) .. '"'
  end
  if t == "table" then
    seen = seen or {}
    if seen[v] then error("json: circular table") end
    seen[v] = true
    local out = {}
    local arr, n = is_array(v)
    if arr and n > 0 then
      for i = 1, n do out[i] = json.encode(v[i], seen) end
      seen[v] = nil
      return "[" .. table.concat(out, ",") .. "]"
    end
    for k, val in pairs(v) do
      out[#out + 1] = json.encode(tostring(k)) .. ":" .. json.encode(val, seen)
    end
    seen[v] = nil
    if #out == 0 then return arr and "[]" or "{}" end
    return "{" .. table.concat(out, ",") .. "}"
  end
  error("json: cannot encode a " .. t)
end

function json.decode(s)
  local pos = 1
  local function ws() pos = s:find("[^ \t\r\n]", pos) or (#s + 1) end
  local function err(msg) error("json: " .. msg .. " at position " .. pos) end
  local value
  local function str()
    pos = pos + 1
    local buf = {}
    while true do
      local c = s:sub(pos, pos)
      if c == "" then err("unterminated string") end
      if c == '"' then pos = pos + 1; break end
      if c == "\\" then
        local e = s:sub(pos + 1, pos + 1)
        local map = { b = "\b", f = "\f", n = "\n", r = "\r", t = "\t", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
        if map[e] then
          buf[#buf + 1] = map[e]; pos = pos + 2
        elseif e == "u" then
          local cp = tonumber(s:sub(pos + 2, pos + 5), 16) or err("bad \\u escape")
          pos = pos + 6
          if cp >= 0xD800 and cp <= 0xDBFF and s:sub(pos, pos + 1) == "\\u" then
            local lo = tonumber(s:sub(pos + 2, pos + 5), 16)
            if lo and lo >= 0xDC00 and lo <= 0xDFFF then
              cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
              pos = pos + 6
            end
          end
          buf[#buf + 1] = utf8char(cp)
        else
          err("bad escape")
        end
      else
        local j = s:find('["\\]', pos) or (#s + 1)
        buf[#buf + 1] = s:sub(pos, j - 1)
        pos = j
      end
    end
    return table.concat(buf)
  end
  function value()
    ws()
    local c = s:sub(pos, pos)
    if c == "{" then
      pos = pos + 1
      local obj = {}
      ws()
      if s:sub(pos, pos) == "}" then pos = pos + 1; return obj end
      while true do
        ws()
        if s:sub(pos, pos) ~= '"' then err("expected a key") end
        local k = str()
        ws()
        if s:sub(pos, pos) ~= ":" then err("expected ':'") end
        pos = pos + 1
        local v = value()
        if v ~= nil then obj[k] = v end
        ws()
        local d = s:sub(pos, pos)
        pos = pos + 1
        if d == "}" then return obj end
        if d ~= "," then err("expected ',' or '}'") end
      end
    elseif c == "[" then
      pos = pos + 1
      local arr, n = {}, 0
      ws()
      if s:sub(pos, pos) == "]" then pos = pos + 1; return arr end
      while true do
        n = n + 1
        local v = value()
        if v == nil then v = rad.null end
        arr[n] = v
        ws()
        local d = s:sub(pos, pos)
        pos = pos + 1
        if d == "]" then return arr end
        if d ~= "," then err("expected ',' or ']'") end
      end
    elseif c == '"' then
      return str()
    elseif s:sub(pos, pos + 3) == "true" then pos = pos + 4; return true
    elseif s:sub(pos, pos + 4) == "false" then pos = pos + 5; return false
    elseif s:sub(pos, pos + 3) == "null" then pos = pos + 4; return nil
    else
      local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", pos)
      if not num or num == "" then err("unexpected character '" .. c .. "'") end
      pos = pos + #num
      local v = tonumber(num)
      if math.tointeger then v = math.tointeger(v) or v end
      return v
    end
  end
  local ok, result = pcall(value)
  if not ok then error(result, 0) end
  return result
end

-- ------------------------------------------------------------------ RAD Hub
local hub, hub_id, has_socket, socket = nil, 0, nil, nil
local IS_WINDOWS = package.config:sub(1, 1) == "\\"

local function connect(name, addr)
  if has_socket == nil then
    has_socket, socket = pcall(require, "socket")
  end
  if not has_socket then return nil end
  local host, port = addr:match("^(.*):(%d+)$")
  local c, e = socket.connect(host, tonumber(port))
  if not c then error("radcall(" .. name .. "): cannot connect to RAD Hub at " .. addr .. ": " .. tostring(e), 0) end
  return c
end

local function shell_quote(s)
  if IS_WINDOWS then return '"' .. s:gsub('"', '\\"') .. '"' end
  return "'" .. s:gsub("'", "'\\''") .. "'"
end

-- one call through the Python helper (no LuaSocket)
local function helper_call(request)
  local tmp = os.tmpname()
  if IS_WINDOWS and not tmp:find("[/\\].*[/\\]") then tmp = (os.getenv("TEMP") or ".") .. tmp end
  local f = assert(io.open(tmp, "wb"))
  f:write(request)
  f:close()
  local py = rawget(_G, "RAD_PYTHON") or os.getenv("RAD_PYTHON") or (IS_WINDOWS and "python" or "python3")
  local script = HERE .. "/radcall_helper.py"
  local probe = io.open(script, "r")
  if probe then probe:close() else script = (os.getenv("RAD_PROJECT") or ".") .. "/radcall_helper.py" end
  local cmd = shell_quote(py) .. " " .. shell_quote(script) .. " " .. shell_quote(tmp)
  if IS_WINDOWS then cmd = '"' .. cmd .. '"' end        -- cmd.exe strips one pair of quotes
  local p = io.popen(cmd, "r")
  local out = p and p:read("*a") or ""
  if p then p:close() end
  os.remove(tmp)
  return out
end

function rad.radcall(name, ...)
  local addr = os.getenv("RAD_HUB")
  if not addr or addr == "" then
    error("radcall(" .. name .. "): RAD Hub is not running (RAD_HUB is not set)", 2)
  end
  local n, args = select("#", ...), {}
  for i = 1, n do
    local v = select(i, ...)
    if v == nil then v = rad.null end
    args[i] = v
  end
  hub_id = hub_id + 1
  local id = hub_id
  local argtext = n > 0 and json.encode(args) or "[]"
  local request = '{"id":' .. id .. ',"call":' .. json.encode(name) .. ',"args":' .. argtext .. "}"
  local lines = {}
  if hub == nil then hub = connect(name, addr) or false end
  if hub then
    local ok, e = hub:send(request .. "\n")
    if not ok then hub = nil; error("radcall(" .. name .. "): " .. tostring(e), 2) end
    while true do
      local line, e2 = hub:receive("*l")
      if not line then hub = nil; error("radcall(" .. name .. "): RAD Hub closed the connection (" .. tostring(e2) .. ")", 2) end
      local okd, msg = pcall(json.decode, line)
      if okd and type(msg) == "table" and msg.id == id then lines = { msg }; break end
    end
  else
    for line in helper_call(request):gmatch("[^\r\n]+") do
      local okd, msg = pcall(json.decode, line)
      if okd and type(msg) == "table" then lines[#lines + 1] = msg end
    end
  end
  local msg = lines[1]
  if not msg then error("radcall(" .. name .. "): no answer from the RAD Hub", 2) end
  if msg.error ~= nil then error("radcall(" .. name .. "): " .. tostring(msg.error), 2) end
  return msg.result
end

-- ------------------------------------------------------------------ main loop
function rad.load_file(file)
  local chunk, e = loadfile(file)
  if not chunk then
    io.stderr:write("[Lua] error in ", file, ": ", tostring(e), "\n")
    return
  end
  local ok, e2 = pcall(chunk)
  if not ok then io.stderr:write("[Lua] error in ", file, ": ", tostring(e2), "\n") end
end

local function find_handler(name)
  local f = rawget(_G, name)
  if type(f) == "function" then return f end
  local lower = name:lower()
  for k, v in pairs(_G) do
    if type(k) == "string" and type(v) == "function" and k:lower() == lower then return v end
  end
  return nil
end

function rad.run()
  while true do
    local line = io.stdin:read("*l")
    if line == nil then break end
    line = line:gsub("\r$", "")
    if line == "QUIT" then break end
    local obj, ev, rest = line:match("^EVENT (%S+) (%S+) ?(.*)$")
    if obj then
      local h = find_handler(obj .. "_" .. ev)
      if h then
        local a = {}
        for w in (rest .. " "):gmatch("([^ ]*) ") do a[#a + 1] = w end
        local e = { X = tonumber(a[1]) or 0, Y = tonumber(a[2]) or 0, Button = tonumber(a[3]) or 0,
          KeyCode = tonumber(a[4]) or 0, KeyChar = a[5] or "", args = rest, object = obj, event = ev }
        local ok, err = xpcall(function() return h(e) end, debug.traceback)
        if not ok then io.stderr:write("[Lua] error in ", obj, "_", ev, ": ", tostring(err), "\n") end
      end
      io.stdout:write("DONE\n")
      io.stdout:flush()
    end
  end
  os.exit(0)
end

-- globals for form code
_G.rad = rad
_G.ui = rad.ui
_G.radcall = rad.radcall
_G.msgbox = rad.msgbox

return rad
