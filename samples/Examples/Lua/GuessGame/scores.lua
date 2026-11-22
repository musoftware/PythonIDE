-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- Module scores - best results per level, saved in best_scores.txt ("level tries seconds" per line).
local M = {}
M.FILE = "best_scores.txt"

function M.load()
  local best = {}
  local f = io.open(M.FILE, "r")
  if not f then return best end
  for line in f:lines() do
    local level, tries, secs = line:match("^(%S+)%s+(%d+)%s+(%d+)")
    if level then best[level] = { tries = tonumber(tries), secs = tonumber(secs) } end
  end
  f:close()
  return best
end

function M.save(best)
  local f = assert(io.open(M.FILE, "w"))
  for level, b in pairs(best) do f:write(level, " ", b.tries, " ", b.secs, "\n") end
  f:close()
end

-- true when (tries, secs) beats the saved result of the level (fewer tries, then less time)
function M.is_better(old, tries, secs)
  if not old then return true end
  return tries < old.tries or (tries == old.tries and secs < old.secs)
end

return M
