# radgame.ring - the RAD IDE game runtime for Ring + RingRayLib (copied into every Ring game project).
#
# It loads a <Scene>.scene file (JSON made by the RAD IDE scene designer, CONTRACTS 10.4) and plays it with
# raylib: tile maps with collision, sprites and sprite-sheet animations, text with {score} / {lives}, a camera
# that follows a sprite, and the Behaviours platformer / keyboard_move / top_down / bounce / follow_mouse /
# enemy_patrol / solid / collectible.  Your code is <Scene>.ring with VB-style handlers:
#
#     func Scene_Load                    the scene starts
#     func Scene_Update dt               every frame
#     func Scene_KeyDown key             "left" "right" "up" "down" "space" "enter" "escape" "a".."z" "0".."9"
#     func Player_Collide oOther         Player touched another object (oOther.name, oOther.group, oOther.destroy())
#     func Player_Jump / Player_OutOfWorld / Coin_Collide oOther (group handler) / Timer1_Tick
#
# Every object of the scene is a global by its name (Player.x += 4, ScoreText.text = "..."), see
# <Scene>_designer.ring.  Helpers: game.score, game.lives, AddScore(n), RestartScene(), GoToScene(name),
# Quit(), ShowMessage(text, seconds), PlayGameSound(id), IsKeyHeld(key), FindObject(name), FindGroup(group),
# AddTimer(name, ms), StopTimer(name).  Object methods: destroy() show() hide() right() bottom() play(anim).
#
# Environment variables for tests: RADGAME_FRAMES=n quits after n frames, RADGAME_KEYS="right:5-90,space:40-50"
# holds keys between frames, RADGAME_SCREENSHOT=file.png saves the last frame, RADGAME_HIDDEN=1 hides the window,
# RADGAME_FIXED_DT=1 uses dt = 1/fps.

load "raylib.ring"
load "jsonlib.ring"

rg_folder = ""
rg_scenes = []                 # [name, handlers-prefix] of the scenes the game knows (main.ring)
rg_data = []                   # the JSON of the running scene (list)
rg_objs = []                   # RGObject
rg_layers = []                 # RGLayer
rg_textures = []               # [path, texture, width, height]
rg_sheets = []                 # [id, texture index, frame_w, frame_h, animations (json list)]
rg_tilesets = []               # [id, texture index, tile_w, tile_h]
rg_images = []                 # [id, texture index]
rg_sounds = []                 # [id, path, sound or NULL]
rg_timers = []                 # [name, interval ms, acc, enabled]
rg_touching = []               # "a|b" pairs touching last frame
rg_held = []                   # key names held now
rg_pressed = []                # key names that went down this frame
rg_script = []                 # [key, from frame, to frame] (RADGAME_KEYS)
rg_audio = false
rg_view_w = 800  rg_view_h = 600  rg_world_w = 800  rg_world_h = 600
rg_cam_x = 0  rg_cam_y = 0  rg_follow = ""
rg_fps = 60  rg_gravity = 900  rg_bg = "#6EC1E4"
rg_error = ""
rg_debug = false               # the RAD IDE debug agent (raddbg.ring) is loaded: trace only your handlers
rg_keymap = [["left", KEY_LEFT], ["right", KEY_RIGHT], ["up", KEY_UP], ["down", KEY_DOWN], ["space", KEY_SPACE],
             ["enter", KEY_ENTER], ["escape", KEY_ESCAPE], ["shift", KEY_LEFT_SHIFT], ["ctrl", KEY_LEFT_CONTROL],
             ["tab", KEY_TAB], ["backspace", KEY_BACKSPACE]]
for rg_i = 0 to 25
    rg_keymap + [char(97 + rg_i), 65 + rg_i]
next
for rg_i = 0 to 9
    rg_keymap + ["" + rg_i, 48 + rg_i]
next
game = new RGGame

# ====================================================================== start
func rg_run cScene, cTitle, cFolder
    rg_debug = isfunction("raddbg_trace")
    rg_trace(false)
    rg_folder = cFolder
    if rg_folder != "" and right(rg_folder, 1) != "/" and right(rg_folder, 1) != "\" rg_folder += "/" ok
    rg_readscript()
    if sysget("RADGAME_HIDDEN") != "" SetConfigFlags(FLAG_WINDOW_HIDDEN) ok
    aFirst = rg_loadjson(cScene)
    InitWindow(rg_num(rg_get(aFirst, "width", 800), 800), rg_num(rg_get(aFirst, "height", 600), 600), cTitle)
    SetExitKey(0)
    InitAudioDevice()
    rg_audio = IsAudioDeviceReady()
    rg_load_scene(cScene)
    nFrames = rg_num(sysget("RADGAME_FRAMES"), 0)
    lFixed = sysget("RADGAME_FIXED_DT") != ""
    cShot = sysget("RADGAME_SCREENSHOT")
    game.running = true
    while game.running and not WindowShouldClose()
        nDt = GetFrameTime()
        if lFixed or nDt <= 0 nDt = 1 / rg_fps ok
        if nDt > 0.05 nDt = 0.05 ok
        rg_step(nDt)
        if nFrames > 0 and game.frame >= nFrames
            if cShot != "" TakeScreenshot(cShot) ok
            exit
        ok
    end
    ? "radgame: " + game.frame + " frames"
    if rg_audio CloseAudioDevice() ok
    CloseWindow()

func rg_readscript
    cKeys = sysget("RADGAME_KEYS")
    if cKeys = "" return ok
    for cPart in str2list(substr(cKeys, ",", nl))
        nColon = substr(cPart, ":")
        if nColon > 0
            cSpan = substr(cPart, nColon + 1)
            nDash = substr(cSpan, "-")
            if nDash > 0
                rg_script + [lower(trim(left(cPart, nColon - 1))), number(left(cSpan, nDash - 1)),
                             number(substr(cSpan, nDash + 1))]
            ok
        ok
    next

# ====================================================================== JSON helpers
func rg_loadjson cName
    cFile = rg_folder + cName + ".scene"
    if not fexists(cFile) raise("radgame: " + cFile + " does not exist") ok
    return json2list(read(cFile))

func rg_get aList, cKey, vDefault
    # the value of key cKey in a JSON object (list of [key, value]); vDefault when missing
    if not islist(aList) return vDefault ok
    cKey = lower(cKey)
    for aItem in aList
        if islist(aItem) and len(aItem) = 2 and isstring(aItem[1])
            if lower(aItem[1]) = cKey
                if isstring(aItem[2]) and aItem[2] = "null" return vDefault ok
                return aItem[2]
            ok
        ok
    next
    return vDefault

func rg_num vValue, nDefault
    if isnumber(vValue) return vValue ok
    if isstring(vValue)
        if vValue = "" or vValue = "null" return nDefault ok
        if isdigit(substr(vValue, "-", "")) or substr(vValue, ".") > 0
            return 0 + number(vValue)
        ok
    ok
    return nDefault

func rg_bool vValue, lDefault
    if isnumber(vValue) return vValue != 0 ok
    if isstring(vValue)
        if vValue = "true" return true ok
        if vValue = "false" or vValue = "" return false ok
        if vValue = "null" return lDefault ok
        return true
    ok
    return lDefault

func rg_str vValue
    if isstring(vValue)
        if vValue = "null" return "" ok
        return vValue
    ok
    if isnumber(vValue) return "" + vValue ok
    return ""

func rg_min a, b
    if a < b return a ok
    return b

func rg_max a, b
    if a > b return a ok
    return b

func rg_color cHex, aDefault
    # "#RRGGBB" -> raylib Color
    cHex = rg_str(cHex)
    if len(cHex) >= 7 and left(cHex, 1) = "#"
        return Color(dec(substr(cHex, 2, 2)), dec(substr(cHex, 4, 2)), dec(substr(cHex, 6, 2)), 255)
    ok
    return Color(aDefault[1], aDefault[2], aDefault[3], 255)

func rg_hit ax, ay, aw, ah, bx, by, bw, bh
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah

# ====================================================================== assets
func rg_texture cRel
    cPath = rg_folder + cRel
    for i = 1 to len(rg_textures)
        if rg_textures[i][1] = cPath return i ok
    next
    if not fexists(cPath)
        ? "radgame: cannot load image " + cRel
        return 0
    ok
    oTex = LoadTexture(cPath)
    rg_textures + [cPath, oTex, oTex.width, oTex.height]
    return len(rg_textures)

func rg_load_assets aAssets
    rg_sheets = []  rg_tilesets = []  rg_images = []  rg_sounds = []
    for aItem in rg_get(aAssets, "images", [])
        rg_images + [aItem[1], rg_texture(rg_str(aItem[2]))]
    next
    for aItem in rg_get(aAssets, "sounds", [])
        rg_sounds + [aItem[1], rg_folder + rg_str(aItem[2]), NULL]
    next
    for aItem in rg_get(aAssets, "spritesheets", [])
        aSh = aItem[2]
        rg_sheets + [aItem[1], rg_texture(rg_str(rg_get(aSh, "image", ""))), rg_num(rg_get(aSh, "frame_w", 32), 32),
                     rg_num(rg_get(aSh, "frame_h", 32), 32), rg_get(aSh, "animations", [])]
    next
    for aItem in rg_get(aAssets, "tilesets", [])
        aTs = aItem[2]
        rg_tilesets + [aItem[1], rg_texture(rg_str(rg_get(aTs, "image", ""))), rg_num(rg_get(aTs, "tile_w", 32), 32),
                       rg_num(rg_get(aTs, "tile_h", 32), 32)]
    next

func rg_sheet_index cId
    for i = 1 to len(rg_sheets)
        if rg_sheets[i][1] = cId return i ok
    next
    return 0

func rg_image_index cId
    for i = 1 to len(rg_images)
        if rg_images[i][1] = cId return rg_images[i][2] ok
    next
    return 0

# ====================================================================== scene
func rg_load_scene cName
    rg_data = rg_loadjson(cName)
    game.scene_name = rg_str(rg_get(rg_data, "name", cName))
    if game.scene_name = "" game.scene_name = cName ok
    rg_view_w = rg_num(rg_get(rg_data, "width", 800), 800)
    rg_view_h = rg_num(rg_get(rg_data, "height", 600), 600)
    rg_fps = rg_max(1, rg_num(rg_get(rg_data, "fps", 60), 60))
    rg_gravity = rg_num(rg_get(rg_data, "gravity", 900), 900)
    rg_bg = rg_str(rg_get(rg_data, "background", "#6EC1E4"))
    SetTargetFPS(rg_fps)
    rg_load_assets(rg_get(rg_data, "assets", []))
    rg_objs = []  rg_layers = []  rg_timers = []  rg_touching = []
    for aL in rg_get(rg_data, "layers", [])
        oLayer = new RGLayer
        oLayer.name = rg_str(rg_get(aL, "name", "Layer"))
        oLayer.type = rg_str(rg_get(aL, "type", "sprites"))
        oLayer.visible = rg_bool(rg_get(aL, "visible", true), true)
        oLayer.collision = rg_bool(rg_get(aL, "collision", false), false)
        cTs = rg_str(rg_get(aL, "tileset", ""))
        for i = 1 to len(rg_tilesets)
            if rg_tilesets[i][1] = cTs
                oLayer.tileset = i
                oLayer.tile_w = rg_tilesets[i][3]
                oLayer.tile_h = rg_tilesets[i][4]
            ok
        next
        oLayer.data = rg_get(aL, "data", [])
        rg_layers + oLayer
        nLayer = len(rg_layers)
        for aO in rg_get(aL, "objects", [])
            rg_add_object(aO, nLayer)
        next
    next
    rg_world_w = rg_view_w  rg_world_h = rg_view_h
    for oL in rg_layers
        if oL.type = "tiles"
            nCols = 0
            for aRow in oL.data
                nCols = rg_max(nCols, len(aRow))
            next
            rg_world_w = rg_max(rg_world_w, nCols * oL.tile_w)
            rg_world_h = rg_max(rg_world_h, len(oL.data) * oL.tile_h)
        ok
    next
    for aT in rg_get(rg_data, "timers", [])
        rg_timers + [rg_str(rg_get(aT, "name", "Timer1")), rg_num(rg_get(aT, "interval", 1000), 1000), 0,
                     rg_bool(rg_get(aT, "enabled", true), true)]
    next
    rg_follow = rg_str(rg_get(rg_get(rg_data, "camera", []), "follow", ""))
    rg_bind_objects()
    rg_camera()
    rg_fire_scene("Load", NULL)

func rg_add_object aO, nLayer
    o = new RGObject
    o.name = rg_str(rg_get(aO, "name", "Object"))
    o.kind = rg_str(rg_get(aO, "kind", "sprite"))
    o.x = rg_num(rg_get(aO, "x", 0), 0)  o.y = rg_num(rg_get(aO, "y", 0), 0)
    o.w = rg_num(rg_get(aO, "w", 0), 0)  o.h = rg_num(rg_get(aO, "h", 0), 0)
    o.scale = rg_num(rg_get(aO, "scale", 1), 1)
    if o.scale = 0 o.scale = 1 ok
    o.rotation = rg_num(rg_get(aO, "rotation", 0), 0)
    o.z = rg_num(rg_get(aO, "z", 0), 0)
    o.visible = rg_bool(rg_get(aO, "visible", true), true)
    o.layer = nLayer
    o.behaviours = rg_get(aO, "behaviours", [])
    o.props = rg_get(aO, "props", [])
    o.group = rg_str(rg_get(o.props, "group", ""))
    if o.group = ""
        o.group = o.name
        while len(o.group) > 1 and isdigit(right(o.group, 1))
            o.group = left(o.group, len(o.group) - 1)
        end
    ok
    o.text = rg_str(rg_get(aO, "text", rg_get(o.props, "Text", "")))
    o.font_size = rg_num(rg_get(o.props, "FontSize", 24), 24)
    o.forecolor = rg_str(rg_get(o.props, "ForeColor", "#FFFFFF"))
    o.backcolor = rg_str(rg_get(o.props, "BackColor", "#E65050"))
    o.align = lower(rg_str(rg_get(o.props, "Align", "left")))
    o.image = rg_image_index(rg_str(rg_get(aO, "image", "")))
    o.sheet = rg_sheet_index(rg_str(rg_get(aO, "spritesheet", "")))
    o.animation = rg_str(rg_get(aO, "animation", ""))
    if o.sheet > 0
        aAnims = rg_sheets[o.sheet][5]
        if o.animation = "" or not islist(rg_get(aAnims, o.animation, 0))
            if len(aAnims) > 0 o.animation = aAnims[1][1] ok
        ok
        if o.w = 0 or o.h = 0 o.w = rg_sheets[o.sheet][3]  o.h = rg_sheets[o.sheet][4] ok
    but o.image > 0
        if o.w = 0 or o.h = 0 o.w = rg_textures[o.image][3]  o.h = rg_textures[o.image][4] ok
    ok
    if o.kind = "sprite"
        if o.w = 0 o.w = 32 ok
        if o.h = 0 o.h = 32 ok
    ok
    o.start_x = o.x  o.start_y = o.y
    o.update_flags()
    rg_objs + o
    return len(rg_objs)

func rg_bind_objects
    # the scene objects become the globals of <Scene>_designer.ring (Player, Coin1 ...)
    cFunc = "rg_bind_" + game.scene_name
    if isfunction(cFunc) call cFunc() ok

func rg_index cName
    cName = lower(cName)
    for i = 1 to len(rg_objs)
        if lower(rg_objs[i].name) = cName return i ok
    next
    return 0

func rg_ref cName
    nIdx = rg_index(cName)
    if nIdx = 0 return NULL ok
    return ref(rg_objs[nIdx])

# ====================================================================== handlers
func rg_trace lOn
    # under the debugger the runtime itself runs untraced (fast); breakpoints work in your handlers
    if not rg_debug return ok
    if lOn ringvm_settrace("RadDbg_Trace()") else ringvm_settrace("") ok

func rg_call cName, vArg, lHasArg
    if not isfunction(cName) return false ok
    rg_trace(true)
    try
        if lHasArg
            call cName(vArg)
        else
            call cName()
        ok
    catch
        if substr(lower(cCatchError), "parameters") > 0
            try
                if lHasArg call cName() else call cName(vArg) ok
            catch
                rg_fail(cName, cCatchError)
            done
        else
            rg_fail(cName, cCatchError)
        ok
    done
    rg_trace(false)
    return true

func rg_fail cWhere, cErr
    rg_error = cWhere + ": " + cErr
    ? "radgame error - " + rg_error

func rg_fire_scene cEvent, vArg
    lArg = not (isstring(vArg) and vArg = "") and not isnull(vArg)
    if cEvent = "Load" lArg = false ok
    aOwners = ["Scene", game.scene_name, "Game"]
    for cOwner in aOwners
        if rg_call(cOwner + "_" + cEvent, vArg, lArg) return true ok
    next
    return false

func rg_fire_object nIdx, cEvent, nOther
    lDone = false
    cName = rg_objs[nIdx].name
    cGroup = rg_objs[nIdx].group
    if nOther > 0
        if rg_call(cName + "_" + cEvent, ref(rg_objs[nOther]), true) lDone = true ok
        if lower(cGroup) != lower(cName)
            if rg_call(cGroup + "_" + cEvent, ref(rg_objs[nOther]), true) lDone = true ok
        ok
    else
        if rg_call(cName + "_" + cEvent, NULL, false) lDone = true ok
        if lower(cGroup) != lower(cName)
            if rg_call(cGroup + "_" + cEvent, NULL, false) lDone = true ok
        ok
    ok
    return lDone

# ====================================================================== input
func rg_input
    rg_pressed = []
    aOld = rg_held
    rg_held = []
    for aK in rg_keymap
        if IsKeyDown(aK[2]) rg_held + aK[1] ok
    next
    for aS in rg_script
        if game.frame >= aS[2] and game.frame < aS[3] and not rg_in(rg_held, aS[1]) rg_held + aS[1] ok
    next
    for cK in rg_held
        if not rg_in(aOld, cK)
            rg_pressed + cK
            rg_fire_scene("KeyDown", cK)
        ok
    next
    for cK in aOld
        if not rg_in(rg_held, cK) rg_fire_scene("KeyUp", cK) ok
    next

func rg_in aList, cValue
    for cItem in aList
        if cItem = cValue return true ok
    next
    return false

func rg_axis cNeg1, cNeg2, cPos1, cPos2
    nAxis = 0
    if rg_in(rg_held, cPos1) or rg_in(rg_held, cPos2) nAxis += 1 ok
    if rg_in(rg_held, cNeg1) or rg_in(rg_held, cNeg2) nAxis -= 1 ok
    return nAxis

# ====================================================================== collision
func rg_blocked nX, nY, nW, nH, nIgnore
    # true when the rectangle touches a solid tile or a solid object
    for oL in rg_layers
        if oL.type = "tiles" and oL.collision
            nC0 = rg_max(0, floor(nX / oL.tile_w))  nC1 = floor((nX + nW - 1) / oL.tile_w)
            nR0 = rg_max(0, floor(nY / oL.tile_h))  nR1 = floor((nY + nH - 1) / oL.tile_h)
            nR1 = rg_min(nR1, len(oL.data) - 1)
            for nR = nR0 to nR1
                aRow = oL.data[nR + 1]
                nLast = rg_min(nC1, len(aRow) - 1)
                for nC = nC0 to nLast
                    if aRow[nC + 1] >= 0 return [nC * oL.tile_w, nR * oL.tile_h, oL.tile_w, oL.tile_h] ok
                next
            next
        ok
    next
    for i = 1 to len(rg_objs)
        if i != nIgnore and rg_objs[i].alive and rg_layers[rg_objs[i].layer].type != "ui"
            if rg_objs[i].f_solid
                nOw = rg_objs[i].w * rg_objs[i].scale  nOh = rg_objs[i].h * rg_objs[i].scale
                if rg_hit(nX, nY, nW, nH, rg_objs[i].x, rg_objs[i].y, nOw, nOh)
                    return [rg_objs[i].x, rg_objs[i].y, nOw, nOh]
                ok
            ok
        ok
    next
    return []

func rg_move nIdx, nDx, nDy
    # move rg_objs[nIdx], stopping at solid tiles / objects. Returns [hit_x, hit_y]
    lHx = false  lHy = false
    nSteps = floor(rg_max(fabs(nDx), fabs(nDy)) / 8) + 1
    nSx = nDx / nSteps  nSy = nDy / nSteps
    for nS = 1 to nSteps
        if nSx != 0 and not lHx
            rg_objs[nIdx].x += nSx
            aB = rg_blocked(rg_objs[nIdx].x, rg_objs[nIdx].y, rg_objs[nIdx].width(), rg_objs[nIdx].height(), nIdx)
            if len(aB) > 0
                if nSx > 0 rg_objs[nIdx].x = aB[1] - rg_objs[nIdx].width() else rg_objs[nIdx].x = aB[1] + aB[3] ok
                lHx = true
            ok
        ok
        if nSy != 0 and not lHy
            rg_objs[nIdx].y += nSy
            aB = rg_blocked(rg_objs[nIdx].x, rg_objs[nIdx].y, rg_objs[nIdx].width(), rg_objs[nIdx].height(), nIdx)
            if len(aB) > 0
                if nSy > 0 rg_objs[nIdx].y = aB[2] - rg_objs[nIdx].height() else rg_objs[nIdx].y = aB[2] + aB[4] ok
                lHy = true
            ok
        ok
    next
    return [lHx, lHy]

func rg_standing nIdx
    nW = rg_objs[nIdx].w * rg_objs[nIdx].scale
    return len(rg_blocked(rg_objs[nIdx].x + 1, rg_objs[nIdx].y + rg_objs[nIdx].h * rg_objs[nIdx].scale,
                          rg_max(1, nW - 2), 1, nIdx)) > 0

func rg_clamp nIdx
    rg_objs[nIdx].x = rg_max(0, rg_min(rg_objs[nIdx].x, rg_world_w - rg_objs[nIdx].width()))
    rg_objs[nIdx].y = rg_max(0, rg_min(rg_objs[nIdx].y, rg_world_h - rg_objs[nIdx].height()))

func rg_auto_anim nIdx, aNames
    nSheet = rg_objs[nIdx].sheet
    if nSheet = 0 return ok
    for cN in aNames
        if islist(rg_get(rg_sheets[nSheet][5], cN, 0))
            rg_objs[nIdx].play(cN)
            return
        ok
    next

func rg_is_actor nIdx
    return rg_objs[nIdx].f_actor

# ====================================================================== behaviours
func rg_behave nIdx, aB, nDt
    cType = rg_str(rg_get(aB, "type", ""))
    switch cType
    on "platformer"     rg_platformer(nIdx, aB, nDt)
    on "keyboard_move"  rg_keyboard_move(nIdx, aB, nDt)
    on "top_down"       rg_top_down(nIdx, aB, nDt)
    on "bounce"         rg_bounce(nIdx, aB, nDt)
    on "follow_mouse"   rg_follow_mouse(nIdx, aB, nDt)
    on "enemy_patrol"   rg_enemy_patrol(nIdx, aB, nDt)
    off

func rg_platformer nIdx, aB, nDt
    nSpeed = rg_num(rg_get(aB, "speed", 220), 220)
    nJump = rg_num(rg_get(aB, "jump", 520), 520)
    nGrav = rg_num(rg_get(aB, "gravity", rg_gravity), rg_gravity)
    nMaxFall = rg_num(rg_get(aB, "max_fall", 900), 900)
    nJumps = rg_num(rg_get(aB, "jumps", 1), 1)
    nIx = rg_axis("left", "a", "right", "d")
    rg_objs[nIdx].vx = nIx * nSpeed
    if nIx != 0 rg_objs[nIdx].flip_x = nIx < 0 ok
    if rg_objs[nIdx].on_ground
        rg_objs[nIdx].st_coyote = 0.1
        rg_objs[nIdx].st_jumps = nJumps
    else
        rg_objs[nIdx].st_coyote = rg_max(0, rg_objs[nIdx].st_coyote - nDt)
    ok
    lJumpHit = rg_in(rg_pressed, "up") or rg_in(rg_pressed, "w") or rg_in(rg_pressed, "space")
    lJumpHeld = rg_in(rg_held, "up") or rg_in(rg_held, "w") or rg_in(rg_held, "space")
    if lJumpHit rg_objs[nIdx].st_buffer = 0.12 else rg_objs[nIdx].st_buffer = rg_max(0, rg_objs[nIdx].st_buffer - nDt) ok
    if rg_objs[nIdx].st_buffer > 0 and (rg_objs[nIdx].st_coyote > 0 or rg_objs[nIdx].st_jumps > 0)
        rg_objs[nIdx].vy = -nJump
        rg_objs[nIdx].st_buffer = 0  rg_objs[nIdx].st_coyote = 0
        rg_objs[nIdx].st_jumps -= 1
        rg_objs[nIdx].on_ground = false
        rg_fire_object(nIdx, "Jump", 0)
    ok
    if rg_objs[nIdx].vy < 0 and not lJumpHeld rg_objs[nIdx].vy += nGrav * nDt * 1.5 ok
    rg_objs[nIdx].vy = rg_min(rg_objs[nIdx].vy + nGrav * nDt, nMaxFall)
    aHit = rg_move(nIdx, rg_objs[nIdx].vx * nDt, rg_objs[nIdx].vy * nDt)
    if aHit[2] rg_objs[nIdx].vy = 0 ok
    rg_objs[nIdx].on_ground = rg_standing(nIdx) and rg_objs[nIdx].vy >= 0
    rg_objs[nIdx].x = rg_max(0, rg_min(rg_objs[nIdx].x, rg_world_w - rg_objs[nIdx].width()))
    if rg_objs[nIdx].on_ground
        if nIx != 0 rg_auto_anim(nIdx, ["run", "walk"]) else rg_auto_anim(nIdx, ["idle"]) ok
    else
        if rg_objs[nIdx].vy < 0 rg_auto_anim(nIdx, ["jump", "fall"]) else rg_auto_anim(nIdx, ["fall", "jump"]) ok
    ok

func rg_keyboard_move nIdx, aB, nDt
    nSpeed = rg_num(rg_get(aB, "speed", 200), 200)
    nIx = rg_axis("left", "a", "right", "d")
    nIy = rg_axis("up", "w", "down", "s")
    cAxis = lower(rg_str(rg_get(aB, "axis", "both")))
    if cAxis = "x" nIy = 0 ok
    if cAxis = "y" nIx = 0 ok
    if nIx != 0 and nIy != 0 nIx *= 0.7071  nIy *= 0.7071 ok
    rg_objs[nIdx].vx = nIx * nSpeed  rg_objs[nIdx].vy = nIy * nSpeed
    if nIx != 0 rg_objs[nIdx].flip_x = nIx < 0 ok
    rg_move(nIdx, rg_objs[nIdx].vx * nDt, rg_objs[nIdx].vy * nDt)
    rg_clamp(nIdx)

func rg_top_down nIdx, aB, nDt
    nSpeed = rg_num(rg_get(aB, "speed", 180), 180)
    nIx = rg_axis("left", "a", "right", "d")
    nIy = rg_axis("up", "w", "down", "s")
    if rg_bool(rg_get(aB, "four_way", false), false) and nIx != 0 and nIy != 0 nIy = 0 ok
    nLen = sqrt(nIx * nIx + nIy * nIy)
    if nLen = 0 nLen = 1 ok
    rg_objs[nIdx].vx = nIx / nLen * nSpeed  rg_objs[nIdx].vy = nIy / nLen * nSpeed
    rg_move(nIdx, rg_objs[nIdx].vx * nDt, rg_objs[nIdx].vy * nDt)
    rg_clamp(nIdx)
    if nIx != 0 or nIy != 0
        if fabs(nIx) >= fabs(nIy)
            if nIx > 0 cD = "right" else cD = "left" ok
        else
            if nIy > 0 cD = "down" else cD = "up" ok
        ok
        rg_objs[nIdx].st_facing = cD
        if rg_bool(rg_get(aB, "rotate", false), false)
            rg_objs[nIdx].rotation = atan2(nIy, nIx) * 180 / 3.14159265
        but nIx != 0
            rg_objs[nIdx].flip_x = nIx < 0 and not rg_has_anim(nIdx, "walk_left")
        ok
        rg_auto_anim(nIdx, ["walk_" + cD, cD, "walk", "run"])
    else
        rg_auto_anim(nIdx, ["idle_" + rg_objs[nIdx].st_facing, "idle"])
    ok

func rg_has_anim nIdx, cName
    nSheet = rg_objs[nIdx].sheet
    if nSheet = 0 return false ok
    return islist(rg_get(rg_sheets[nSheet][5], cName, 0))

func rg_bounce nIdx, aB, nDt
    if not rg_objs[nIdx].st_init
        rg_objs[nIdx].st_init = true
        rg_objs[nIdx].vx = rg_num(rg_get(aB, "vx", 150), 150)
        rg_objs[nIdx].vy = rg_num(rg_get(aB, "vy", 150), 150)
    ok
    aHit = rg_move(nIdx, rg_objs[nIdx].vx * nDt, rg_objs[nIdx].vy * nDt)
    lHx = aHit[1]  lHy = aHit[2]
    o = rg_objs[nIdx]
    if o.x < 0 or o.x + o.width() > rg_world_w lHx = true ok
    if o.y < 0 or o.y + o.height() > rg_world_h lHy = true ok
    rg_clamp(nIdx)
    if lHx rg_objs[nIdx].vx = -rg_objs[nIdx].vx ok
    if lHy rg_objs[nIdx].vy = -rg_objs[nIdx].vy ok
    if lHx or lHy rg_fire_object(nIdx, "Bounce", 0) ok

func rg_follow_mouse nIdx, aB, nDt
    oPos = GetMousePosition()
    nMx = oPos.x  nMy = oPos.y
    if rg_layers[rg_objs[nIdx].layer].type != "ui" nMx += rg_cam_x  nMy += rg_cam_y ok
    rg_objs[nIdx].x = nMx - rg_objs[nIdx].width() / 2
    rg_objs[nIdx].y = nMy - rg_objs[nIdx].height() / 2

func rg_enemy_patrol nIdx, aB, nDt
    nSpeed = rg_num(rg_get(aB, "speed", 80), 80)
    nDist = rg_num(rg_get(aB, "distance", 160), 160)
    cAxis = lower(rg_str(rg_get(aB, "axis", "x")))
    if rg_objs[nIdx].st_dir = 0
        rg_objs[nIdx].st_dir = 1
        if rg_bool(rg_get(aB, "start_left", false), false) rg_objs[nIdx].st_dir = -1 ok
        if cAxis = "x" rg_objs[nIdx].st_origin = rg_objs[nIdx].x else rg_objs[nIdx].st_origin = rg_objs[nIdx].y ok
    ok
    nD = rg_objs[nIdx].st_dir
    if cAxis = "y"
        aHit = rg_move(nIdx, 0, nD * nSpeed * nDt)
        lTurn = aHit[2]
        nPos = rg_objs[nIdx].y
    else
        if rg_bool(rg_get(aB, "gravity", true), true) and rg_gravity != 0
            rg_objs[nIdx].vy = rg_min(rg_objs[nIdx].vy + rg_gravity * nDt, 900)
            aHit = rg_move(nIdx, 0, rg_objs[nIdx].vy * nDt)
            if aHit[2] rg_objs[nIdx].vy = 0 ok
            rg_objs[nIdx].on_ground = rg_standing(nIdx)
        ok
        aHit = rg_move(nIdx, nD * nSpeed * nDt, 0)
        lTurn = aHit[1]
        nPos = rg_objs[nIdx].x
        if rg_objs[nIdx].on_ground and rg_bool(rg_get(aB, "turn_at_edges", true), true)
            if nD > 0 nFx = rg_objs[nIdx].x + rg_objs[nIdx].width() + 1 else nFx = rg_objs[nIdx].x - 1 ok
            if len(rg_blocked(nFx, rg_objs[nIdx].y + rg_objs[nIdx].height() + 2, 1, 1, nIdx)) = 0 lTurn = true ok
        ok
        rg_objs[nIdx].flip_x = nD < 0
        rg_auto_anim(nIdx, ["walk", "run"])
    ok
    if nDist > 0 and fabs(nPos - rg_objs[nIdx].st_origin) >= nDist and (nPos - rg_objs[nIdx].st_origin) * nD > 0
        lTurn = true
    ok
    if lTurn rg_objs[nIdx].st_dir = -nD ok

# ====================================================================== frame
func rg_step nDt
    rg_input()
    for nT = 1 to len(rg_timers)
        if nT > len(rg_timers) exit ok
        if rg_timers[nT][4] and rg_timers[nT][2] > 0
            rg_timers[nT][3] += nDt * 1000
            while nT <= len(rg_timers) and rg_timers[nT][3] >= rg_timers[nT][2] - 0.001 and rg_timers[nT][4]
                rg_timers[nT][3] -= rg_timers[nT][2]
                rg_call(rg_timers[nT][1] + "_Tick", NULL, false)
            end
        ok
    next
    nCount = len(rg_objs)
    for i = 1 to nCount
        if i > len(rg_objs) exit ok
        if rg_objs[i].alive
            for aB in rg_objs[i].behaviours
                rg_behave(i, aB, nDt)
                if i > len(rg_objs) exit ok
            next
            if i > len(rg_objs) exit ok
            rg_objs[i].anim_time += nDt
            if rg_objs[i].alive and rg_objs[i].y > rg_world_h + 200 and rg_layers[rg_objs[i].layer].type != "ui"
                if not rg_fire_object(i, "OutOfWorld", 0)
                    if rg_is_actor(i) RestartScene() else rg_objs[i].destroy() ok
                ok
            ok
        ok
    next
    rg_collisions()
    rg_fire_scene("Update", nDt)
    if game.pending_scene != ""
        cNext = game.pending_scene
        game.pending_scene = ""
        rg_load_scene(cNext)
    ok
    rg_camera()
    rg_draw()
    game.frame += 1
    game.time += nDt

func rg_collisions
    aNow = []
    aR = []
    for i = 1 to len(rg_objs)
        if rg_objs[i].alive and rg_objs[i].kind != "text" and rg_layers[rg_objs[i].layer].type != "ui"
            aR + [i, rg_objs[i].x, rg_objs[i].y, rg_objs[i].w * rg_objs[i].scale, rg_objs[i].h * rg_objs[i].scale]
        ok
    next
    nCount = len(aR)
    for p = 1 to nCount
        for q = p + 1 to nCount
            if rg_hit(aR[p][2], aR[p][3], aR[p][4], aR[p][5], aR[q][2], aR[q][3], aR[q][4], aR[q][5])
                aNow + [aR[p][1], aR[q][1], rg_objs[aR[p][1]].name + "|" + rg_objs[aR[q][1]].name]
            ok
        next
    next
    aKeep = []
    for aP in aNow
        aKeep + aP[3]
        if rg_in(rg_touching, aP[3]) loop ok
        i = aP[1]  j = aP[2]
        if not rg_objs[i].alive or not rg_objs[j].alive loop ok
        for aAB in [[i, j], [j, i]]
            if rg_objs[aAB[2]].f_collect and rg_objs[aAB[1]].f_actor and rg_objs[aAB[2]].alive
                aColl = rg_objs[aAB[2]].behaviour("collectible")
                game.score += rg_num(rg_get(aColl, "score", 1), 1)
                cSnd = rg_str(rg_get(aColl, "sound", ""))
                if cSnd != "" PlayGameSound(cSnd) ok
            ok
        next
        rg_fire_object(i, "Collide", j)
        rg_fire_object(j, "Collide", i)
        for aAB in [[i, j], [j, i]]
            if rg_objs[aAB[2]].f_collect and rg_objs[aAB[1]].f_actor rg_objs[aAB[2]].destroy() ok
        next
    next
    rg_touching = aKeep

func rg_camera
    if rg_follow != ""
        nIdx = rg_index(rg_follow)
        if nIdx > 0
            rg_cam_x = rg_objs[nIdx].x + rg_objs[nIdx].width() / 2 - rg_view_w / 2
            rg_cam_y = rg_objs[nIdx].y + rg_objs[nIdx].height() / 2 - rg_view_h / 2
        ok
    ok
    rg_cam_x = rg_max(0, rg_min(rg_cam_x, rg_world_w - rg_view_w))
    rg_cam_y = rg_max(0, rg_min(rg_cam_y, rg_world_h - rg_view_h))

# ====================================================================== drawing
func rg_draw
    BeginDrawing()
    ClearBackground(rg_color(rg_bg, [110, 193, 228]))
    oWhite = Color(255, 255, 255, 255)
    nOx = floor(rg_cam_x)  nOy = floor(rg_cam_y)
    for nL = 1 to len(rg_layers)
        oL = rg_layers[nL]
        if not oL.visible loop ok
        if oL.type = "tiles"
            rg_draw_tiles(oL, nOx, nOy, oWhite)
        else
            nX0 = nOx  nY0 = nOy
            if oL.type = "ui" nX0 = 0  nY0 = 0 ok
            aOrder = []
            for i = 1 to len(rg_objs)
                if rg_objs[i].layer = nL and rg_objs[i].visible and rg_objs[i].alive aOrder + [rg_objs[i].z, i] ok
            next
            aOrder = sort(aOrder, 1)
            for aZ in aOrder
                rg_draw_object(aZ[2], nX0, nY0, oWhite)
            next
        ok
    next
    rg_fire_scene("Draw", NULL)
    if game.message != "" and game.time < game.message_until rg_banner(game.message, Color(0, 0, 0, 255)) ok
    if rg_error != "" rg_banner("Error: " + rg_error, Color(139, 0, 0, 255)) ok
    EndDrawing()

func rg_banner cText, oBg
    nW = MeasureText(cText, 30) + 32
    nX = floor((rg_view_w - nW) / 2)  nY = floor(rg_view_h / 2) - 25
    DrawRectangle(nX, nY, nW, 50, oBg)
    DrawText(cText, nX + 16, nY + 10, 30, GPData(Color(255, 255, 255, 255)))

func rg_draw_tiles oL, nOx, nOy, oWhite
    if oL.tileset = 0 return ok
    nTex = rg_tilesets[oL.tileset][2]
    if nTex = 0 return ok
    oTex = rg_textures[nTex][2]
    nTw = oL.tile_w  nTh = oL.tile_h
    nCols = rg_max(1, floor(rg_textures[nTex][3] / nTw))
    nC0 = rg_max(0, floor(nOx / nTw))  nC1 = floor((nOx + rg_view_w) / nTw)
    nR0 = rg_max(0, floor(nOy / nTh))  nR1 = rg_min(floor((nOy + rg_view_h) / nTh), len(oL.data) - 1)
    for nR = nR0 to nR1
        aRow = oL.data[nR + 1]
        nLast = rg_min(nC1, len(aRow) - 1)
        for nC = nC0 to nLast
            nT = aRow[nC + 1]
            if nT >= 0
                DrawTextureRec(oTex, Rectangle((nT % nCols) * nTw, floor(nT / nCols) * nTh, nTw, nTh),
                               Vector2(nC * nTw - nOx, nR * nTh - nOy), oWhite)
            ok
        next
    next

func rg_draw_object nIdx, nOx, nOy, oWhite
    o = rg_objs[nIdx]
    if o.kind = "text"
        cText = o.display_text()
        nSize = floor(o.font_size)
        nX = o.x - nOx
        if o.w > 0
            nTw = MeasureText(cText, nSize)
            if substr(o.align, "center") > 0 nX += (o.w * o.scale - nTw) / 2 ok
            if substr(o.align, "right") > 0 nX += o.w * o.scale - nTw ok
        ok
        DrawText(cText, floor(nX), floor(o.y - nOy), nSize, GPData(rg_color(o.forecolor, [255, 255, 255])))
        return
    ok
    if o.kind = "area" return ok
    nW = o.width()  nH = o.height()
    nTex = 0  nSx = 0  nSy = 0  nSw = 0  nSh = 0
    if o.sheet > 0 and rg_sheets[o.sheet][2] > 0
        nTex = rg_sheets[o.sheet][2]
        nSw = rg_sheets[o.sheet][3]  nSh = rg_sheets[o.sheet][4]
        nCols = rg_max(1, floor(rg_textures[nTex][3] / nSw))
        nRows = rg_max(1, floor(rg_textures[nTex][4] / nSh))
        nF = rg_frame(nIdx) % (nCols * nRows)
        nSx = (nF % nCols) * nSw  nSy = floor(nF / nCols) * nSh
    but o.image > 0
        nTex = o.image
        nSw = rg_textures[nTex][3]  nSh = rg_textures[nTex][4]
    ok
    if nTex = 0
        DrawRectangle(floor(o.x - nOx), floor(o.y - nOy), floor(nW), floor(nH), rg_color(o.backcolor, [230, 80, 80]))
        return
    ok
    if o.flip_x nSw = -nSw ok
    DrawTexturePro(rg_textures[nTex][2], Rectangle(nSx, nSy, nSw, nSh),
                   Rectangle(o.x + nW / 2 - nOx, o.y + nH / 2 - nOy, nW, nH), Vector2(nW / 2, nH / 2), o.rotation, oWhite)

func rg_frame nIdx
    aAnim = rg_get(rg_sheets[rg_objs[nIdx].sheet][5], rg_objs[nIdx].animation, 0)
    if not islist(aAnim) return 0 ok
    aFrames = rg_get(aAnim, "frames", [0])
    if len(aFrames) = 0 return 0 ok
    nFps = rg_num(rg_get(aAnim, "fps", 8), 8)
    nStep = 0
    if nFps > 0 nStep = floor(rg_objs[nIdx].anim_time * nFps) ok
    if rg_bool(rg_get(aAnim, "loop", true), true) return aFrames[(nStep % len(aFrames)) + 1] ok
    return aFrames[rg_min(nStep, len(aFrames) - 1) + 1]

# ====================================================================== VB-style helpers (your code)
func AddScore nPoints
    game.score += nPoints

func RestartScene
    game.pending_scene = game.scene_name

func GoToScene cName
    game.pending_scene = cName

func Quit
    game.running = false

func ShowMessage cText, nSeconds
    game.message = "" + cText
    game.message_until = game.time + nSeconds

func PlayGameSound cId
    if not rg_audio return ok
    for nS = 1 to len(rg_sounds)
        if rg_sounds[nS][1] = cId
            if isnull(rg_sounds[nS][3]) and fexists(rg_sounds[nS][2]) rg_sounds[nS][3] = LoadSound(rg_sounds[nS][2]) ok
            if not isnull(rg_sounds[nS][3]) PlaySound(rg_sounds[nS][3]) ok
            return
        ok
    next

func IsKeyHeld cKey
    return rg_in(rg_held, lower(cKey))

func FindObject cName
    return rg_ref(cName)

func FindGroup cGroup
    aOut = []
    for i = 1 to len(rg_objs)
        if rg_objs[i].alive and lower(rg_objs[i].group) = lower(cGroup) aOut + rg_objs[i].name ok
    next
    return aOut

func AddTimer cName, nMs
    for nT = 1 to len(rg_timers)
        if lower(rg_timers[nT][1]) = lower(cName)
            rg_timers[nT][2] = nMs  rg_timers[nT][3] = 0  rg_timers[nT][4] = true
            return
        ok
    next
    rg_timers + [cName, nMs, 0, true]

func StopTimer cName
    for nT = 1 to len(rg_timers)
        if lower(rg_timers[nT][1]) = lower(cName) rg_timers[nT][4] = false ok
    next

# ====================================================================== classes
class RGGame
    score = 0  lives = 3  vars = []  running = false  frame = 0  time = 0
    scene_name = ""  pending_scene = ""  message = ""  message_until = 0

class RGLayer
    name = ""  type = "sprites"  visible = true  collision = false  tileset = 0  tile_w = 32  tile_h = 32  data = []

class RGObject
    name = ""  kind = "sprite"  x = 0  y = 0  w = 0  h = 0  scale = 1  rotation = 0  z = 0  visible = true
    alive = true  layer = 1  group = ""  behaviours = []  props = []  vx = 0  vy = 0  on_ground = false
    flip_x = false  start_x = 0  start_y = 0  text = ""  font_size = 24  forecolor = "#FFFFFF"
    backcolor = "#E65050"  align = "left"  image = 0  sheet = 0  animation = ""  anim_time = 0
    st_coyote = 0  st_buffer = 0  st_jumps = 0  st_dir = 0  st_origin = 0  st_init = false  st_facing = "down"
    data = []  f_solid = false  f_actor = false  f_collect = false

    func update_flags
        f_solid = has("solid")
        f_collect = has("collectible")
        f_actor = has("platformer") or has("keyboard_move") or has("top_down") or has("follow_mouse")

    func width
        return w * scale

    func height
        return h * scale

    func right
        return x + w * scale

    func bottom
        return y + h * scale

    func destroy
        alive = false
        visible = false

    func show
        visible = true

    func hide
        visible = false

    func has cType
        for aB in behaviours
            if rg_str(rg_get(aB, "type", "")) = cType return true ok
        next
        return false

    func behaviour cType
        for aB in behaviours
            if rg_str(rg_get(aB, "type", "")) = cType return aB ok
        next
        return []

    func clear_behaviours
        behaviours = []
        update_flags()

    func play cAnim
        if cAnim != animation
            animation = cAnim
            anim_time = 0
        ok

    func display_text
        cOut = text
        cOut = substr(cOut, "{score}", "" + game.score)
        cOut = substr(cOut, "{lives}", "" + game.lives)
        cOut = substr(cOut, "{level}", game.scene_name)
        return cOut
