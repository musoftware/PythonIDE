# Debug_LuaBridge

**Lua: debugger (round 7, radide/debug_more.py)** - a form with a text box, a Greet button and a label.
`cmdGreet_Click` has locals (a string, a number, a table/hash/list) and calls a helper function, so you can
try breakpoints, Locals, Watch, Step Into / Over / Out.

**Engine:** radide/debug/raddbg_agent.lua (debug.sethook agent, named pipe to the IDE)

**Try it:** open `project.radproj`, put a breakpoint (F9) on line 17 of `Form1.lua`
(the line that calls the helper), press F5, click **Greet**. The IDE stops there: Locals show `name`,
`info`, ... (expand the table). F11 steps into the helper, Shift+F11 steps out, F5 continues.
Conditional breakpoints (`clicks == 2` style, in the language's syntax), hit counts and logpoints work too.
