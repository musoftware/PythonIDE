-- RAD IDE mod test: drive DABG's menus and save screenshots with FCEUX's own Lua API (gui.savescreenshotas)
local out = OUTDIR
local function wait(n) for i=1,n do emu.frameadvance() end end
local function shot(name) gui.savescreenshotas(out .. "/" .. name .. ".png"); wait(2) end
local function press(b) for i=1,6 do joypad.set(1, {[b]=true}); emu.frameadvance() end; wait(30) end
wait(120); shot("01_title")
press("start"); wait(30); shot("02_menu")
press("start"); wait(30); shot("03_who")
press("A"); press("start"); wait(20); shot("04_mode")
press("A"); wait(20); shot("05_difficulty")
press("A"); wait(20); shot("06_level")
press("A"); wait(90); shot("07_game")
for i=1,240 do joypad.set(1, {right=(i<90), left=(i>=90), B=(i%16<8), A=(i%60<10)}); emu.frameadvance() end
shot("08_game_play")
-- read the lives counter of player 1 (zero page $76, PlayerLives in the source)
local f = io.open(out .. "/done.txt", "w"); if f then f:write("lives=" .. memory.readbyte(0x76)); f:close() end
while true do emu.frameadvance() end
