local GoLib = require("GoLib.ref")
local LuaLib = require("LuaLib.ref")
local RbLib = require("RbLib.ref")
local PyLib = require("PyLib.ref")
local CsLib = require("CsLib.ref")
local M = {}
function M.T_GoLib() return GoLib.Add(2, 3) end
function M.T_LuaLib() return LuaLib.Add(2, 3) end
function M.T_RbLib() return RbLib.Add(2, 3) end
function M.T_PyLib() return PyLib.Add(2, 3) end
function M.T_CsLib() return CsLib.Add(2, 3) end
return M
