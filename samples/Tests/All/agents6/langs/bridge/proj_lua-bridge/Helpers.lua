local M = {}
function M.add(a, b) print("logged add") return a + b end
function M.greet(w) return "Hello, " .. w end
function M.info() return { a = {1, 2}, s = "x" } end
function M.fail() error("bad thing") end
return M
