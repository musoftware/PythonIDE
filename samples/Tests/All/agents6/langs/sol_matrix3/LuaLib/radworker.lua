-- RAD IDE - RAD Hub worker for Lua modules.
--
--   lua radworker.lua <module file>          (cwd = project folder)
--
-- Loads the module and serves its functions over stdin/stdout (JSON lines):
--   stdin : {"id": 7, "func": "add", "args": [2, 3]}
--   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
-- The module may return a table of functions (local M = {} ... return M) or define
-- global functions. print() output goes to stderr so stdout stays clean.
local rad = require("rad")
rad.worker = true
local json = rad.json

local file = arg and arg[1]
if not file then
  io.stderr:write("usage: lua radworker.lua <module file>\n")
  os.exit(2)
end

-- print -> stderr
_G.print = function(...)
  local n, parts = select("#", ...), {}
  for i = 1, n do parts[i] = tostring((select(i, ...))) end
  io.stderr:write(table.concat(parts, "\t"), "\n")
end

local module, load_error = nil, nil
do
  local chunk, e = loadfile(file)
  if not chunk then
    load_error = "error loading " .. file .. ": " .. tostring(e)
  else
    local ok, result = pcall(chunk)
    if not ok then
      load_error = "error loading " .. file .. ": " .. tostring(result)
    elseif type(result) == "table" then
      module = result
    end
  end
  if load_error then io.stderr:write("[radworker] ", load_error, "\n") end
end
local stem = file:match("([^/\\]+)$"):gsub("%.[^.]*$", "")

local function find(name)
  for _, t in ipairs({ module or {}, _G }) do
    local f = rawget(t, name)
    if type(f) == "function" then return f end
  end
  local lower = name:lower()
  for _, t in ipairs({ module or {}, _G }) do
    for k, v in pairs(t) do
      if type(k) == "string" and type(v) == "function" and k:lower() == lower then return v end
    end
  end
  return nil
end

local function reply(id, key, value)
  local ok, text = pcall(function()
    return '{"id":' .. json.encode(id) .. ',"' .. key .. '":' .. json.encode(value) .. "}"
  end)
  if not ok then
    text = '{"id":' .. json.encode(id) .. ',"error":' .. json.encode("result is not JSON: " .. tostring(text)) .. "}"
  end
  io.stdout:write(text, "\n")
  io.stdout:flush()
end

local unpack = table.unpack or unpack
for line in io.stdin:lines() do
  line = line:gsub("\r$", "")
  if line:find("%S") then
    local okd, req = pcall(json.decode, line)
    if not okd or type(req) ~= "table" then
      reply(rad.null, "error", "bad request")
    else
      local id = req.id
      if id == nil then id = rad.null end
      local name = tostring(req.func or "")
      local f = find(name)
      if load_error then
        reply(id, "error", load_error)
      elseif not f then
        reply(id, "error", stem .. " has no function '" .. name .. "'")
      else
        local args = type(req.args) == "table" and req.args or {}
        local n = #args
        for i = 1, n do if args[i] == rad.null then args[i] = nil end end
        local ok, result = pcall(f, unpack(args, 1, n))
        if ok then
          reply(id, "result", result)
        else
          reply(id, "error", tostring(result))
        end
      end
    end
  end
end
