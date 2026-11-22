-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Module calc - a small expression evaluator (numbers, + - * /, parentheses, unary minus).
-- Used by Form1.lua with: local calc = require("calc"). No load()/eval: the text is parsed by hand.
local M = {}

local function tokenize(s)
  local tokens, i = {}, 1
  while i <= #s do
    local c = s:sub(i, i)
    if c:match("%s") then
      i = i + 1
    elseif c:match("[%d%.]") then
      local num = s:match("^%d*%.?%d*", i)
      if num == "." or num == "" then error("bad number at position " .. i) end
      tokens[#tokens + 1] = { kind = "num", value = tonumber(num) }
      i = i + #num
    elseif c:match("[%+%-%*/%(%)]") then
      tokens[#tokens + 1] = { kind = "op", value = c }
      i = i + 1
    else
      error("unexpected '" .. c .. "'")
    end
  end
  return tokens
end

-- recursive descent: expr := term {(+|-) term};  term := factor {(*|/) factor};  factor := [-] (num | "(" expr ")")
function M.evaluate(text)
  local tokens, pos = tokenize(text), 1
  local function peek() return tokens[pos] end
  local function take() pos = pos + 1; return tokens[pos - 1] end
  local expr
  local function factor()
    local t = take()
    if not t then error("incomplete expression") end
    if t.kind == "op" and t.value == "-" then return -factor() end
    if t.kind == "num" then return t.value end
    if t.value == "(" then
      local v = expr()
      local close = take()
      if not close or close.value ~= ")" then error("missing )") end
      return v
    end
    error("unexpected '" .. t.value .. "'")
  end
  local function term()
    local v = factor()
    while peek() and (peek().value == "*" or peek().value == "/") do
      local op = take().value
      local r = factor()
      if op == "*" then v = v * r else
        if r == 0 then error("division by zero") end
        v = v / r
      end
    end
    return v
  end
  expr = function()
    local v = term()
    while peek() and (peek().value == "+" or peek().value == "-") do
      local op = take().value
      local r = term()
      v = (op == "+") and v + r or v - r
    end
    return v
  end
  local v = expr()
  if pos <= #tokens then error("unexpected '" .. tokens[pos].value .. "'") end
  return v
end

-- 12.0 -> "12", 0.1 + 0.2 -> "0.3" (10 significant digits)
function M.format(v)
  if v == math.floor(v) and math.abs(v) < 1e15 then return string.format("%d", v) end
  local s = string.format("%.10g", v)
  return s
end

return M
