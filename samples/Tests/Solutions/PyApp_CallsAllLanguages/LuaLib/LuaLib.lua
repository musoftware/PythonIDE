-- Class library LuaLib. The functions of the returned table can be called from every
-- project that references this library, in its own language, e.g.
--   Python: import LuaLib; LuaLib.Add(2, 3)     Lua: local LuaLib = require("LuaLib.ref")
local M = {}

--- Add two numbers.
function M.Add(a, b)
  return a + b
end

--- Greeting text for who.
function M.Greet(who)
  return "Hello, " .. who .. "!"
end

return M
