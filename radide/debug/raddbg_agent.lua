-- RAD IDE debug agent for Lua (radide/debug_more.py, AgentSession). Pure Lua 5.1-5.4, no C modules.
-- Loaded before the program:  lua -e "dofile([[...raddbg_agent.lua]])" _radmain.lua
-- Talks to the IDE over a Windows named pipe (QLocalServer): one connection to write (opened first),
-- one to read. Breakpoints come from the file RADDBG_BPFILE ("path<TAB>line<TAB>cond<TAB>hit<TAB>log"),
-- re-read when it changes (checked once per second while code runs, and on every resume).
local PIPE = os.getenv("RADDBG_PIPE")
if not PIPE or PIPE == "" then return end
local BPFILE = os.getenv("RADDBG_BPFILE") or ""
local CWD = (os.getenv("RADDBG_CWD") or "."):gsub("\\", "/"):lower():gsub("/$", "")

local getinfo, getlocal, getupvalue, sethook = debug.getinfo, debug.getlocal, debug.getupvalue, debug.sethook
local unpack = table.unpack or unpack
local load_ = loadstring and function(src, name, env)
  local f, e = loadstring(src, name)
  if f and env then setfenv(f, env) end
  return f, e
end or function(src, name, env) return load(src, name, "t", env) end

local function open_retry(mode)
  for _ = 1, 4000 do
    local f = io.open(PIPE, mode)
    if f then return f end
    local t = os.clock() + 0.005
    while os.clock() < t do end
  end
  return nil
end

local out = open_retry("wb")
if not out then io.stderr:write("[debugger] cannot reach the IDE pipe\n") return end
out:setvbuf("no")
local inp = open_retry("rb")
if not inp then io.stderr:write("[debugger] cannot reach the IDE pipe\n") return end

local function esc(s)
  s = tostring(s)
  return (s:gsub("\\", "\\\\"):gsub("\t", "\\t"):gsub("\n", "\\n"):gsub("\r", "\\r"))
end
local function unesc(s)
  return (s:gsub("\\(.)", function(c)
    if c == "t" then return "\t" elseif c == "n" then return "\n" elseif c == "r" then return "\r" end
    return c
  end))
end
local function send(...)
  local t = { ... }
  for i = 1, select("#", ...) do t[i] = esc(t[i] == nil and "" or t[i]) end
  out:write(table.concat(t, "\t"), "\n")
  out:flush()
end
local function recv()
  local line = inp:read("*l")
  if not line then return nil end
  line = line:gsub("\r$", "")
  local parts = {}
  for p in (line .. "\t"):gmatch("([^\t]*)\t") do parts[#parts + 1] = unesc(p) end
  return parts
end

-- ------------------------------------------------------------------ paths / breakpoints
local keycache = {}
local function key_of(source)
  local k = keycache[source]
  if k then return k end
  local s = source
  if s:sub(1, 1) == "@" then s = s:sub(2) else keycache[source] = false return false end
  s = s:gsub("\\", "/"):lower()
  while s:sub(1, 2) == "./" do s = s:sub(3) end
  if not (s:match("^%a:/") or s:sub(1, 1) == "/") then s = CWD .. "/" .. s end
  s = s:gsub("/%./", "/")
  keycache[source] = s
  return s
end

local SKIP = { ["rad.lua"] = true, ["raddbg_agent.lua"] = true, ["radworker.lua"] = true }
local function skipped(key)
  if not key then return true end
  return SKIP[key:match("[^/]+$") or ""] or false
end

local bps = {}        -- line -> { key -> {cond, hit, log, count} }
local bptext = nil
local break_on_error = false   -- "!exc<TAB>1" in the breakpoint file (Debug > Break on Exceptions)
local function load_bps(force)
  local f = BPFILE ~= "" and io.open(BPFILE, "rb")
  if not f then return end
  local text = f:read("*a") or ""
  f:close()
  if text == bptext and not force then return end
  bptext = text
  local old, new = bps, {}
  break_on_error = false
  for l in text:gmatch("[^\n]+") do
    local p = {}
    for x in (l:gsub("\r$", "") .. "\t"):gmatch("([^\t]*)\t") do p[#p + 1] = unesc(x) end
    local line = tonumber(p[2])
    if p[1] == "!exc" then
      break_on_error = p[2] == "1"
    elseif p[1] and line then
      new[line] = new[line] or {}
      local prev = old[line] and old[line][p[1]]
      new[line][p[1]] = { cond = p[3] or "", hit = p[4] or "", log = p[5] or "",
                          count = prev and prev.cond == (p[3] or "") and prev.count or 0 }
    end
  end
  bps = new
end

-- ------------------------------------------------------------------ values
local refs, nextref = {}, 0
local function ref_of(v)
  if type(v) ~= "table" then return 0 end
  for i = 1, nextref do if refs[i] == v then return i end end
  nextref = nextref + 1
  refs[nextref] = v
  return nextref
end
local function show(v)
  local t = type(v)
  if t == "string" then return (string.format("%q", v):gsub("\\\n", "\\n")) end
  if t == "table" then
    local n = 0
    for _ in pairs(v) do n = n + 1 if n > 999 then break end end
    return "table (" .. n .. (n > 999 and "+" or "") .. " entries)"
  end
  local ok, s = pcall(tostring, v)
  return ok and s or ("<" .. t .. ">")
end

local snapshot = {}   -- locals + upvalues of the stopped frame (name -> value)
local function capture(level)
  snapshot = {}
  local vars = {}
  local i = 1
  while true do
    local name, val = getlocal(level, i)
    if not name then break end
    if name:sub(1, 1) ~= "(" then
      snapshot[name] = { val }
      vars[#vars + 1] = { name, val }
    end
    i = i + 1
  end
  local info = getinfo(level, "f")
  if info and info.func then
    i = 1
    while true do
      local name, val = getupvalue(info.func, i)
      if not name then break end
      if name ~= "_ENV" and snapshot[name] == nil then
        snapshot[name] = { val }
        vars[#vars + 1] = { name, val }
      end
      i = i + 1
    end
  end
  return vars
end

local env = setmetatable({}, { __index = function(_, k)
  local s = snapshot[k]
  if s then return s[1] end
  return _G[k]
end })

local function eval(expr)
  local f, e = load_("return " .. expr, "=watch", env)
  if not f then f, e = load_(expr, "=watch", env) end
  if not f then return false, e end
  local r = { pcall(f) }
  if not r[1] then return false, r[2] end
  return true, r[2]
end

local function format_log(msg)
  return (msg:gsub("{([^{}]+)}", function(x)
    local ok, v = eval(x)
    return ok and (type(v) == "string" and v or show(v)) or ("<" .. tostring(v) .. ">")
  end))
end

-- ------------------------------------------------------------------ stopping
local mode = "run"     -- run | step | next | out
local step_depth = 0

local function depth_from(level)
  local d = 0
  while getinfo(level + d, "l") do d = d + 1 end
  return d
end

local function global_name(f)
  for k, v in pairs(_G) do
    if v == f and type(k) == "string" then return k end
  end
  return nil
end

local function stopped_loop(level, reason)
  refs, nextref = {}, 0
  local info = getinfo(level, "Sl")
  send("stop", reason, info.source:gsub("^@", ""), info.currentline)
  local l = level
  while true do
    local fi = getinfo(l, "Slnf")
    if not fi then break end
    if fi.what ~= "C" and fi.source:sub(1, 1) == "@" and not skipped(key_of(fi.source)) then
      send("frame", fi.name or (fi.what == "main" and "(main chunk)") or global_name(fi.func) or "?",
           fi.source:sub(2), fi.currentline)
    end
    l = l + 1
  end
  for _, nv in ipairs(capture(level + 1)) do
    local v = nv[2]
    send("var", nv[1], type(v), show(v), ref_of(v))
  end
  send("end")
  while true do
    local cmd = recv()
    if not cmd then sethook() return end
    local c = cmd[1]
    if c == "c" then mode = "run" break
    elseif c == "s" then mode = "step" break
    elseif c == "n" then mode = "next" step_depth = depth_from(level + 1) break
    elseif c == "o" then mode = "out" step_depth = depth_from(level + 1) break
    elseif c == "q" then sethook() return
    elseif c == "e" then
      local ok, v = eval(cmd[3] or "")
      if ok then send("result", cmd[2], show(v), type(v), ref_of(v))
      else send("result", cmd[2], "error: " .. tostring(v), "error", 0) end
    elseif c == "v" then
      local t = refs[tonumber(cmd[3]) or 0]
      send("vars", cmd[2])
      if type(t) == "table" then
        local keys = {}
        for k in pairs(t) do keys[#keys + 1] = k if #keys >= 500 then break end end
        table.sort(keys, function(a, b)
          if type(a) == "number" and type(b) == "number" then return a < b end
          return tostring(a) < tostring(b)
        end)
        for _, k in ipairs(keys) do
          local v = t[k]
          send("var", type(k) == "number" and ("[" .. k .. "]") or tostring(k), type(v), show(v), ref_of(v))
        end
      end
      send("end")
    end
  end
  load_bps(true)
end

local last_t = 0
local function hook(event, line)
  if event ~= "line" then return end
  local t = os.time()
  if t ~= last_t then last_t = t load_bps(false) end
  if mode ~= "run" then
    local info = getinfo(2, "S")
    local k = key_of(info.source)
    if k and not skipped(k) then
      if mode == "step" then stopped_loop(3, "step") return end
      local d = depth_from(3)
      if (mode == "next" and d <= step_depth) or (mode == "out" and d < step_depth) then
        stopped_loop(3, "step")
        return
      end
    end
  end
  local bl = bps[line]
  if not bl then return end
  local info = getinfo(2, "S")
  local b = bl[key_of(info.source)]
  if not b then return end
  if b.cond ~= "" then
    capture(3)
    local ok, v = eval(b.cond)
    if not ok or not v then return end
  end
  b.count = b.count + 1
  if b.hit ~= "" then
    local op, n = b.hit:match("^%s*([=><%%]*)%s*(%d+)%s*$")
    n = tonumber(n)
    if n then
      local c = b.count
      local pass = (op == ">=" and c >= n) or (op == ">" and c > n) or (op == "%" and n > 0 and c % n == 0)
                   or ((op == "" or op == "=" or op == "==") and c == n)
      if not pass then return end
    end
  end
  if b.log ~= "" then
    capture(3)
    send("out", format_log(b.log))
    return
  end
  stopped_loop(3, "breakpoint")
end

send("hello", "lua", _VERSION)
while true do                      -- wait for the IDE: breakpoints are written, then "run"
  local cmd = recv()
  if not cmd or cmd[1] == "run" then break end
end
load_bps(true)
sethook(hook, "l")
-- coroutines get their own hook
local cocreate, cowrap = coroutine.create, coroutine.wrap
coroutine.create = function(f) local co = cocreate(f) sethook(co, hook, "l") return co end
coroutine.wrap = function(f)
  local co = coroutine.create(f)
  return function(...)
    local r = { coroutine.resume(co, ...) }
    if not r[1] then error(r[2], 2) end
    return unpack(r, 2)
  end
end
-- Break on Exceptions: rad.lua runs every handler with xpcall(..., debug.traceback); the message handler runs
-- where the error happened (the stack is still there), so the agent's traceback stops there first
local orig_traceback = debug.traceback
debug.traceback = function(msg, ...)
  if break_on_error and msg ~= nil and select("#", ...) == 0 then
    local i2 = getinfo(2, "Sn")
    local from_error = i2 and ((i2.what == "C" and i2.name == "error") or
                               (type(msg) == "string" and msg:match(":%d+: ") ~= nil))
    if from_error then
      local l = 2
      while true do                      -- the first frame of the program's own code
        local fi = getinfo(l, "S")
        if not fi then l = nil break end
        if fi.what ~= "C" and fi.source:sub(1, 1) == "@" and not skipped(key_of(fi.source)) then break end
        l = l + 1
      end
      if l then
        sethook()
        stopped_loop(l + 1, "exception")
        sethook(hook, "l")
      end
    end
  end
  return orig_traceback(msg, ...)
end
_G.__raddbg = { eval = eval }
