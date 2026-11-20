/* radgame.js - the RAD IDE game runtime for HTML5 Canvas (copied into every HTML5 game project).
 *
 * The same scenes (<Scene>.scene, RAD IDE CONTRACTS 10.4) and the same Behaviours as radgame.py (pygame):
 * tile maps with collision, sprites and sprite-sheet animations, text with {score} / {lives}, a camera
 * that follows a sprite, keyboard_move / platformer / top_down / bounce / follow_mouse / enemy_patrol /
 * solid / collectible.  Your code is <Scene>.js with VB-style handlers (plain global functions):
 *
 *     function Scene_Load() { game.score = 0; }
 *     function Scene_KeyDown(key) { if (key === "escape") Quit(); }     // "left", "space", "a", "enter" ...
 *     function Player_Collide(other) { if (other.group === "Enemy") RestartScene(); }
 *
 * Every object of the scene is a global by its name (Player.x += 4, ScoreText.text = "...").
 * Handlers: Scene_Load, Scene_Update(dt), Scene_KeyDown(key), Scene_KeyUp(key), Scene_MouseDown(x, y, button),
 * Scene_MouseUp(x, y, button), Scene_Draw(ctx), <Obj>_Click(), <Obj>_Collide(other), <Obj>_AnimationEnd(),
 * <Obj>_OutOfWorld(), <Obj>_Jump(), <Obj>_Bounce(), <Timer>_Tick().  Coin1, Coin2 ... also fire Coin_Collide.
 *
 * scenes.js (written by RAD IDE when a scene is saved and before every run) registers the scene data with
 * RadGame.addScene({...}), so index.html also works when it is opened straight from the disk.
 * URL parameters for tests: ?frames=n stops after n frames, ?fixed=1 uses dt = 1/fps.
 */
(function (global) {
  "use strict";

  var VERSION = "1.0";
  var ACTOR_BEHAVIOURS = ["platformer", "keyboard_move", "top_down", "follow_mouse"];
  var DIRS = { left: ["left", "a"], right: ["right", "d"], up: ["up", "w"], down: ["down", "s"] };
  var JUMP_KEYS = ["up", "w", "space"];
  var KEY_NAMES = { arrowleft: "left", arrowright: "right", arrowup: "up", arrowdown: "down", " ": "space",
    spacebar: "space", enter: "enter", escape: "escape", esc: "escape", shift: "shift", control: "ctrl",
    alt: "alt", backspace: "backspace", tab: "tab", delete: "delete" };

  function num(v, d) { var n = parseFloat(v); return isNaN(n) ? (d === undefined ? 0 : d) : n; }
  function has(list, v) { return list.indexOf(v) >= 0; }
  function rect(x, y, w, h) { return { x: x, y: y, w: w, h: h }; }
  function hit(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
  function keyName(e) {
    var k = (e.key || "").toLowerCase();
    if (KEY_NAMES[k]) return KEY_NAMES[k];
    return k.length === 1 ? k : k;
  }

  // ==================================================================== input
  function Input() {
    this.held = {}; this.pressed = {}; this.released = {};
    this.mouse = [0, 0]; this.buttons = {}; this.queue = [];
  }
  Input.prototype.press = function (key) {
    key = String(key).toLowerCase();
    if (!this.held[key]) { this.held[key] = true; this.pressed[key] = true; this.queue.push(["KeyDown", [key]]); }
  };
  Input.prototype.release = function (key) {
    key = String(key).toLowerCase();
    if (this.held[key]) { delete this.held[key]; this.released[key] = true; this.queue.push(["KeyUp", [key]]); }
  };
  Input.prototype.click = function (x, y, button) {
    this.mouse = [x, y];
    this.queue.push(["MouseDown", [x, y, button || 1]]);
    this.queue.push(["MouseUp", [x, y, button || 1]]);
  };
  Input.prototype.down = function () {
    for (var i = 0; i < arguments.length; i++) {
      var a = arguments[i];
      if (Array.isArray(a)) { for (var j = 0; j < a.length; j++) if (this.held[a[j]]) return true; }
      else if (this.held[String(a).toLowerCase()]) return true;
    }
    return false;
  };
  Input.prototype.hit = function (keys) {
    for (var i = 0; i < keys.length; i++) if (this.pressed[keys[i]]) return true;
    return false;
  };
  Input.prototype.axis = function (neg, pos) { return (this.down(pos) ? 1 : 0) - (this.down(neg) ? 1 : 0); };
  Input.prototype.newFrame = function () { this.pressed = {}; this.released = {}; };

  // ==================================================================== objects
  function GameObject(scene, d, layer) {
    this.scene = scene; this.layer = layer;
    this.kind = "object";
    this.name = String(d.name || "Object");
    this.x = num(d.x); this.y = num(d.y); this.w = num(d.w); this.h = num(d.h);
    this.scale = num(d.scale, 1) || 1; this.rotation = num(d.rotation); this.z = Math.round(num(d.z));
    this.visible = d.visible === undefined ? true : !!d.visible;
    this.props = Object.assign({}, d.props || {});
    this.behaviours = (d.behaviours || []).filter(function (b) { return b && typeof b === "object"; })
      .map(function (b) { return Object.assign({}, b); });
    this.group = String(this.props.group || this.name.replace(/\d+$/, "") || this.name);
    this.vx = 0; this.vy = 0; this.on_ground = false; this.alive = true; this.flip_x = false;
    this.start = [this.x, this.y]; this.data = {}; this._state = {};
  }
  Object.defineProperties(GameObject.prototype, {
    width: { get: function () { return this.w * this.scale; } },
    height: { get: function () { return this.h * this.scale; } },
    right: { get: function () { return this.x + this.width; } },
    bottom: { get: function () { return this.y + this.height; } },
    center: { get: function () { return [this.x + this.width / 2, this.y + this.height / 2]; } },
    rect: { get: function () {
      return rect(Math.round(this.x), Math.round(this.y), Math.max(1, Math.round(this.width)),
        Math.max(1, Math.round(this.height)));
    } },
    solid: { get: function () { return this.alive && this.has("solid"); } }
  });
  GameObject.prototype.overlaps = function (o) { return this.alive && o.alive && hit(this.rect, o.rect); };
  GameObject.prototype.contains = function (x, y) { var r = this.rect; return x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h; };
  GameObject.prototype.move_to = function (x, y) { this.x = +x; this.y = +y; };
  GameObject.prototype.distance_to = function (o) {
    var a = this.center, b = o.center; return Math.hypot(a[0] - b[0], a[1] - b[1]);
  };
  GameObject.prototype.has = function (t) { return this.behaviours.some(function (b) { return b.type === t; }); };
  GameObject.prototype.behaviour = function (t) {
    for (var i = 0; i < this.behaviours.length; i++) if (this.behaviours[i].type === t) return this.behaviours[i];
    return null;
  };
  GameObject.prototype.destroy = function () { this.alive = false; this.visible = false; };
  GameObject.prototype.show = function () { this.visible = true; };
  GameObject.prototype.hide = function () { this.visible = false; };
  GameObject.prototype.update_animation = function () {};
  GameObject.prototype.draw = function () {};
  GameObject.prototype.toString = function () { return "<" + this.kind + " " + this.name + ">"; };

  function Sprite(scene, d, layer) {
    GameObject.call(this, scene, d, layer);
    this.kind = "sprite";
    this.image_id = String(d.image || ""); this.sheet_id = String(d.spritesheet || "");
    this.animation = String(d.animation || "");
    this.color = this.props.color || this.props.BackColor || "#E65050";
    this.anim_time = 0; this.anim_done = false;
    var sheet = scene.sheets[this.sheet_id];
    if (sheet) {
      if (!this.animation || !sheet.animations[this.animation]) this.animation = Object.keys(sheet.animations)[0] || "";
      if (!this.w || !this.h) { this.w = sheet.frame_w; this.h = sheet.frame_h; }
    } else if (scene.images[this.image_id]) {
      var img = scene.images[this.image_id];
      if (!this.w || !this.h) { this.w = img.naturalWidth; this.h = img.naturalHeight; }
    }
    if (!this.w || !this.h) { this.w = this.w || 32; this.h = this.h || 32; }
  }
  Sprite.prototype = Object.create(GameObject.prototype);
  Sprite.prototype.play = function (animation, restart) {
    var sheet = this.scene.sheets[this.sheet_id];
    if (!sheet || !sheet.animations[animation]) return;
    if (animation !== this.animation || restart) { this.animation = animation; this.anim_time = 0; this.anim_done = false; }
  };
  Sprite.prototype.has_animation = function (a) {
    var sheet = this.scene.sheets[this.sheet_id]; return !!(sheet && sheet.animations[a]);
  };
  Sprite.prototype.set_image = function (id) {
    if (this.scene.images[id]) { this.image_id = id; this.sheet_id = ""; }
  };
  Sprite.prototype.frame_index = function () {
    var sheet = this.scene.sheets[this.sheet_id];
    if (!sheet) return 0;
    var anim = sheet.animations[this.animation];
    if (!anim) return 0;
    var frames = (anim.frames && anim.frames.length) ? anim.frames : [0];
    var fps = num(anim.fps, 8);
    var step = fps > 0 ? Math.floor(this.anim_time * fps) : 0;
    if (anim.loop === undefined || anim.loop) return frames[step % frames.length];
    return frames[Math.min(step, frames.length - 1)];
  };
  Sprite.prototype.update_animation = function (dt) {
    var sheet = this.scene.sheets[this.sheet_id];
    if (!sheet) return;
    this.anim_time += dt;
    var anim = sheet.animations[this.animation];
    if (anim && anim.loop === false && !this.anim_done) {
      var fps = num(anim.fps, 8);
      if (fps > 0 && this.anim_time * fps >= (anim.frames || [0]).length) {
        this.anim_done = true;
        this.scene.game.fireObject(this, "AnimationEnd");
      }
    }
  };
  Sprite.prototype.draw = function (ctx, ox, oy) {
    var sheet = this.scene.sheets[this.sheet_id], img = null, sx = 0, sy = 0, sw = 0, sh = 0;
    if (sheet && sheet.image && sheet.image.complete && sheet.image.naturalWidth) {
      var cols = Math.max(1, Math.floor(sheet.image.naturalWidth / sheet.frame_w));
      var rows = Math.max(1, Math.floor(sheet.image.naturalHeight / sheet.frame_h));
      var i = this.frame_index() % (cols * rows);
      img = sheet.image; sw = sheet.frame_w; sh = sheet.frame_h;
      sx = (i % cols) * sw; sy = Math.floor(i / cols) * sh;
    } else if (this.scene.images[this.image_id] && this.scene.images[this.image_id].naturalWidth) {
      img = this.scene.images[this.image_id]; sw = img.naturalWidth; sh = img.naturalHeight;
    }
    var w = Math.max(1, Math.round(this.width)), h = Math.max(1, Math.round(this.height));
    var c = this.center;
    ctx.save();
    ctx.translate(Math.round(c[0] - ox), Math.round(c[1] - oy));
    if (this.rotation) ctx.rotate(this.rotation * Math.PI / 180);
    if (this.flip_x) ctx.scale(-1, 1);
    if (img) ctx.drawImage(img, sx, sy, sw, sh, -w / 2, -h / 2, w, h);
    else { ctx.fillStyle = this.color; ctx.fillRect(-w / 2, -h / 2, w, h); }
    ctx.restore();
  };

  function TextObject(scene, d, layer) {
    GameObject.call(this, scene, d, layer);
    this.kind = "text";
    this.text = String(d.text !== undefined ? d.text : (this.props.Text || ""));
    this.font_size = num(this.props.FontSize, 24);
    this.font_name = this.props.FontName || "";
    this.bold = !!this.props.FontBold;
    this.color = this.props.ForeColor || this.props.color || "#FFFFFF";
    this.align = String(this.props.Align || this.props.TextAlign || "left").toLowerCase();
  }
  TextObject.prototype = Object.create(GameObject.prototype);
  TextObject.prototype.display_text = function () {
    var g = this.scene.game, values = Object.assign({ score: g.score, lives: g.lives, level: this.scene.name }, g.vars);
    return this.text.replace(/\{(\w+)\}/g, function (m, k) { return values[k] !== undefined ? String(values[k]) : m; });
  };
  TextObject.prototype.draw = function (ctx, ox, oy) {
    var px = Math.round(this.font_size * (this.font_name ? 1.33 : 1.0));
    ctx.font = (this.bold ? "bold " : "") + px + "px " + (this.font_name ? '"' + this.font_name + '", ' : "") +
      "Segoe UI, Arial, sans-serif";
    ctx.textBaseline = "top";
    var text = this.display_text(), tw = ctx.measureText(text).width;
    if (!this.w || !this.h) { this.w = tw; this.h = px; }
    var x = this.x - ox;
    if (has(["center", "middlecenter", "topcenter"], this.align)) x += (this.width - tw) / 2;
    else if (has(["right", "middleright", "topright"], this.align)) x += this.width - tw;
    ctx.fillStyle = this.color;
    ctx.fillText(text, Math.round(x), Math.round(this.y - oy));
  };

  function Area(scene, d, layer) { GameObject.call(this, scene, d, layer); this.kind = "area"; }
  Area.prototype = Object.create(GameObject.prototype);
  Area.prototype.draw = function (ctx, ox, oy) {
    if (!this.scene.game.debug) return;
    var r = this.rect; ctx.strokeStyle = "#FFFF00"; ctx.strokeRect(r.x - ox + 0.5, r.y - oy + 0.5, r.w, r.h);
  };

  // ==================================================================== layers
  function Layer(scene, d) {
    this.scene = scene;
    this.name = String(d.name || "Layer"); this.type = String(d.type || "sprites");
    this.visible = d.visible === undefined ? true : !!d.visible;
    this.collision = !!d.collision; this.tileset_id = String(d.tileset || "");
    this.data = (d.data || []).map(function (row) { return row.map(function (v) { return Math.round(num(v, -1)); }); });
    var ts = scene.tilesets[this.tileset_id];
    this.tile_w = ts ? ts.tile_w : 32; this.tile_h = ts ? ts.tile_h : 32;
    this.objects = []; this._cache = null;
  }
  Object.defineProperties(Layer.prototype, {
    screen_space: { get: function () { return this.type === "ui"; } },
    cols: { get: function () { return this.data.reduce(function (m, r) { return Math.max(m, r.length); }, 0); } },
    rows: { get: function () { return this.data.length; } }
  });
  Layer.prototype.tile_at = function (c, r) {
    return (r >= 0 && r < this.data.length && c >= 0 && c < this.data[r].length) ? this.data[r][c] : -1;
  };
  Layer.prototype.set_tile = function (c, r, t) {
    if (r >= 0 && r < this.data.length && c >= 0 && c < this.data[r].length) { this.data[r][c] = t | 0; this._cache = null; }
  };
  Layer.prototype.tile_at_point = function (x, y) { return this.tile_at(Math.floor(x / this.tile_w), Math.floor(y / this.tile_h)); };
  Layer.prototype.solid_rects = function (r) {
    if (!this.collision || this.type !== "tiles") return [];
    var out = [], tw = this.tile_w, th = this.tile_h;
    var c0 = Math.max(0, Math.floor(r.x / tw)), c1 = Math.floor((r.x + r.w - 1) / tw);
    var r0 = Math.max(0, Math.floor(r.y / th)), r1 = Math.floor((r.y + r.h - 1) / th);
    for (var row = r0; row <= Math.min(r1, this.rows - 1); row++) {
      var line = this.data[row];
      for (var c = c0; c <= Math.min(c1, line.length - 1); c++) if (line[c] >= 0) out.push(rect(c * tw, row * th, tw, th));
    }
    return out;
  };
  Layer.prototype.render = function () {
    var ts = this.scene.tilesets[this.tileset_id], cv = document.createElement("canvas");
    cv.width = Math.max(1, this.cols * this.tile_w); cv.height = Math.max(1, this.rows * this.tile_h);
    var ctx = cv.getContext("2d"), ok = ts && ts.image && ts.image.complete && ts.image.naturalWidth;
    var cols = ok ? Math.max(1, Math.floor(ts.image.naturalWidth / ts.tile_w)) : 1;
    var count = ok ? cols * Math.max(1, Math.floor(ts.image.naturalHeight / ts.tile_h)) : 0;
    for (var r = 0; r < this.data.length; r++) {
      for (var c = 0; c < this.data[r].length; c++) {
        var t = this.data[r][c];
        if (t < 0) continue;
        if (ok && t < count) {
          ctx.drawImage(ts.image, (t % cols) * ts.tile_w, Math.floor(t / cols) * ts.tile_h, ts.tile_w, ts.tile_h,
            c * this.tile_w, r * this.tile_h, this.tile_w, this.tile_h);
        } else { ctx.fillStyle = "#785A3C"; ctx.fillRect(c * this.tile_w, r * this.tile_h, this.tile_w, this.tile_h); }
      }
    }
    return cv;
  };
  Layer.prototype.draw = function (ctx, ox, oy) {
    if (!this.visible) return;
    if (this.type === "tiles") {
      if (!this._cache) this._cache = this.render();
      ctx.drawImage(this._cache, -Math.round(ox), -Math.round(oy));
      return;
    }
    if (this.screen_space) { ox = 0; oy = 0; }
    var objs = this.objects.slice().sort(function (a, b) { return a.z - b.z; });
    for (var i = 0; i < objs.length; i++) if (objs[i].visible && objs[i].alive) objs[i].draw(ctx, ox, oy);
  };

  // ==================================================================== camera, timers
  function Camera(scene, d) { this.scene = scene; this.follow = d.follow || null; this.x = num(d.x); this.y = num(d.y); }
  Camera.prototype.update = function () {
    var s = this.scene, t = this.follow ? s.objects[this.follow] : null;
    if (t) { var c = t.center; this.x = c[0] - s.view_w / 2; this.y = c[1] - s.view_h / 2; }
    this.x = Math.max(0, Math.min(this.x, s.world_w - s.view_w));
    this.y = Math.max(0, Math.min(this.y, s.world_h - s.view_h));
  };
  Camera.prototype.to_world = function (x, y) { return [x + this.x, y + this.y]; };
  Camera.prototype.to_screen = function (x, y) { return [x - this.x, y - this.y]; };

  function Timer(name, interval, enabled) {
    this.name = name; this.interval = num(interval, 1000); this.enabled = enabled === undefined ? true : !!enabled; this._acc = 0;
  }
  Timer.prototype.start = function () { this.enabled = true; this._acc = 0; };
  Timer.prototype.stop = function () { this.enabled = false; };

  // ==================================================================== scene
  function Scene(game, name, data) {
    this.game = game; this.data = data; this.name = String(data.name || name);
    this.width = Math.round(num(data.width, 800)); this.height = Math.round(num(data.height, 600));
    this.fps = Math.max(1, Math.round(num(data.fps, 60)));
    this.gravity = num(data.gravity, 900); this.background = data.background || "#6EC1E4";
    this.images = {}; this.sounds = {}; this.sheets = {}; this.tilesets = {};
    this.loadAssets(data.assets || {});
    var self = this, lds = (data.layers || []).filter(function (l) { return l && typeof l === "object"; });
    this.layers = lds.map(function (ld) { return new Layer(self, ld); });
    this.objects = {};
    lds.forEach(function (ld, i) { (ld.objects || []).forEach(function (od) { self.add_object(od, self.layers[i]); }); });
    this.camera = new Camera(this, data.camera || {});
    this.timers = {};
    (data.timers || []).forEach(function (td) {
      var t = new Timer(String(td.name || "Timer1"), num(td.interval, 1000), td.enabled === undefined ? true : !!td.enabled);
      self.timers[t.name] = t;
    });
    this.view_w = this.width; this.view_h = this.height;
    var w = this.width, h = this.height, world = data.world || {};
    w = Math.max(w, num(world.width)); h = Math.max(h, num(world.height));
    this.layers.forEach(function (ly) {
      if (ly.type === "tiles") { w = Math.max(w, ly.cols * ly.tile_w); h = Math.max(h, ly.rows * ly.tile_h); }
    });
    this.world_w = w; this.world_h = h;
    this.camera.update();
  }
  Scene.prototype.image = function (rel) {
    var g = this.game, img = g.imageCache[rel];
    if (!img) {
      img = g.imageCache[rel] = new Image();
      g.pending++;
      img.onload = img.onerror = function (e) {
        g.pending--;
        if (e && e.type === "error") console.error("radgame: cannot load image " + rel);
        g.invalidateTiles();
      };
      img.src = rel;
    }
    return img;
  };
  Scene.prototype.loadAssets = function (a) {
    var self = this, k;
    for (k in (a.images || {})) this.images[k] = this.image(a.images[k]);
    for (k in (a.sounds || {})) this.sounds[k] = a.sounds[k];
    for (k in (a.spritesheets || {})) {
      var sh = a.spritesheets[k], anims = Object.assign({}, sh.animations || {});
      if (!Object.keys(anims).length) anims = { "default": { frames: [0], fps: 8, loop: true } };
      self.sheets[k] = { image: this.image(sh.image || ""), frame_w: Math.round(num(sh.frame_w, 32)),
        frame_h: Math.round(num(sh.frame_h, 32)), animations: anims };
    }
    for (k in (a.tilesets || {})) {
      var ts = a.tilesets[k];
      self.tilesets[k] = { image: this.image(ts.image || ""), tile_w: Math.round(num(ts.tile_w, 32)),
        tile_h: Math.round(num(ts.tile_h, 32)) };
    }
  };
  Scene.prototype.add_object = function (d, layer) {
    var Cls = d.kind === "text" ? TextObject : (d.kind === "area" ? Area : Sprite);
    var o = new Cls(this, d, layer), base = o.name, i = 2;
    while (this.objects[o.name]) o.name = base + "_" + (i++);
    layer.objects.push(o); this.objects[o.name] = o;
    return o;
  };
  Scene.prototype.all_objects = function () {
    var out = []; this.layers.forEach(function (ly) { out.push.apply(out, ly.objects); }); return out;
  };
  Scene.prototype.live_objects = function () { return this.all_objects().filter(function (o) { return o.alive; }); };
  Scene.prototype.blockers = function (r, ignore) {
    var out = [];
    this.layers.forEach(function (ly) { if (ly.type === "tiles" && ly.collision) out.push.apply(out, ly.solid_rects(r)); });
    this.all_objects().forEach(function (o) {
      if (o !== ignore && o.solid && !o.layer.screen_space) { var orr = o.rect; if (hit(orr, r)) out.push(orr); }
    });
    return out;
  };
  Scene.prototype.is_solid_at = function (x, y, ignore) { return this.blockers(rect(Math.floor(x), Math.floor(y), 1, 1), ignore).length > 0; };

  // ==================================================================== movement
  function moveAndCollide(o, dx, dy) {
    var scene = o.scene, hx = false, hy = false;
    var steps = Math.max(1, Math.floor(Math.max(Math.abs(dx), Math.abs(dy)) / 8) + 1), sx = dx / steps, sy = dy / steps;
    for (var s = 0; s < steps; s++) {
      var r, bs, i;
      if (sx && !hx) {
        o.x += sx; r = o.rect; bs = scene.blockers(r, o);
        for (i = 0; i < bs.length; i++) if (hit(r, bs[i])) { o.x = sx > 0 ? bs[i].x - o.width : bs[i].x + bs[i].w; hx = true; r = o.rect; }
      }
      if (sy && !hy) {
        o.y += sy; r = o.rect; bs = scene.blockers(r, o);
        for (i = 0; i < bs.length; i++) if (hit(r, bs[i])) { o.y = sy > 0 ? bs[i].y - o.height : bs[i].y + bs[i].h; hy = true; r = o.rect; }
      }
    }
    return [hx, hy];
  }
  function standing(o) {
    var r = o.rect; return o.scene.blockers(rect(r.x + 1, r.y + r.h, Math.max(1, r.w - 2), 1), o).length > 0;
  }
  function keysOf(b, dir) {
    var which = String(b.keys || "both").toLowerCase(), k = DIRS[dir];
    return which === "arrows" ? [k[0]] : (which === "wasd" ? [k[1]] : k);
  }
  function autoAnim(o) {
    if (!(o instanceof Sprite)) return;
    for (var i = 1; i < arguments.length; i++) if (o.has_animation(arguments[i])) { o.play(arguments[i]); return; }
  }

  var Behaviours = {
    keyboard_move: function (g, o, b, dt) {
      var speed = num(b.speed, 200), ix = g.input.axis(keysOf(b, "left"), keysOf(b, "right"));
      var iy = g.input.axis(keysOf(b, "up"), keysOf(b, "down")), axis = String(b.axis || "both").toLowerCase();
      if (axis === "x") iy = 0; else if (axis === "y") ix = 0;
      if (ix && iy) { ix *= 0.7071; iy *= 0.7071; }
      o.vx = ix * speed; o.vy = iy * speed;
      if (ix) o.flip_x = ix < 0;
      moveAndCollide(o, o.vx * dt, o.vy * dt); g.clampToWorld(o);
    },
    top_down: function (g, o, b, dt) {
      var speed = num(b.speed, 180), ix = g.input.axis(keysOf(b, "left"), keysOf(b, "right"));
      var iy = g.input.axis(keysOf(b, "up"), keysOf(b, "down"));
      if (b.four_way && ix && iy) iy = 0;
      var n = Math.hypot(ix, iy) || 1;
      o.vx = ix / n * speed; o.vy = iy / n * speed;
      moveAndCollide(o, o.vx * dt, o.vy * dt); g.clampToWorld(o);
      if (ix || iy) {
        if (b.rotate) o.rotation = Math.atan2(iy, ix) * 180 / Math.PI;
        var d = Math.abs(ix) >= Math.abs(iy) ? (ix > 0 ? "right" : "left") : (iy > 0 ? "down" : "up");
        o._state.facing = d;
        if (!b.rotate && ix) o.flip_x = ix < 0 && !(o instanceof Sprite && o.has_animation("walk_left"));
        autoAnim(o, "walk_" + d, d, "walk", "run");
      } else autoAnim(o, "idle_" + (o._state.facing || "down"), "idle");
    },
    platformer: function (g, o, b, dt) {
      var speed = num(b.speed, 220), jump = num(b.jump, 520), gravity = num(b.gravity, g.scene.gravity || 900);
      var maxFall = num(b.max_fall, 900), jumps = Math.round(num(b.jumps, 1)), st = o._state;
      var ix = g.input.axis(keysOf(b, "left"), keysOf(b, "right"));
      o.vx = ix * speed;
      if (ix) o.flip_x = ix < 0;
      st.coyote = o.on_ground ? 0.1 : Math.max(0, (st.coyote || 0) - dt);
      if (o.on_ground) st.jumps_left = jumps;
      var up = keysOf(b, "up"), jk = JUMP_KEYS.filter(function (k) { return has(up, k) || k === "space"; });
      st.buffer = g.input.hit(jk) ? 0.12 : Math.max(0, (st.buffer || 0) - dt);
      if (st.buffer > 0 && (st.coyote > 0 || (st.jumps_left || 0) > 0)) {
        o.vy = -jump; st.buffer = 0; st.coyote = 0;
        st.jumps_left = (st.jumps_left === undefined ? jumps : st.jumps_left) - 1;
        o.on_ground = false; g.fireObject(o, "Jump");
      }
      if (o.vy < 0 && !g.input.down(jk)) o.vy += gravity * dt * 1.5;
      o.vy = Math.min(o.vy + gravity * dt, maxFall);
      var h = moveAndCollide(o, o.vx * dt, o.vy * dt);
      if (h[1]) o.vy = 0;
      o.on_ground = standing(o) && o.vy >= 0;
      o.x = Math.max(0, Math.min(o.x, g.scene.world_w - o.width));
      if (o.on_ground) { if (ix) autoAnim(o, "run", "walk"); else autoAnim(o, "idle"); }
      else if (o.vy < 0) autoAnim(o, "jump", "fall"); else autoAnim(o, "fall", "jump");
    },
    bounce: function (g, o, b, dt) {
      var st = o._state;
      if (!st.init) {
        st.init = true;
        if (b.speed !== undefined && b.vx === undefined) {
          var ang = num(b.angle, 45) * Math.PI / 180, sp = num(b.speed, 200);
          o.vx = Math.cos(ang) * sp; o.vy = Math.sin(ang) * sp;
        } else { o.vx = num(b.vx, 150); o.vy = num(b.vy, 150); }
      }
      var h = moveAndCollide(o, o.vx * dt, o.vy * dt), hx = h[0], hy = h[1], s = g.scene;
      if (o.x < 0 || o.right > s.world_w) { o.x = Math.max(0, Math.min(o.x, s.world_w - o.width)); hx = true; }
      if (o.y < 0 || o.bottom > s.world_h) { o.y = Math.max(0, Math.min(o.y, s.world_h - o.height)); hy = true; }
      if (hx) o.vx = -o.vx;
      if (hy) o.vy = -o.vy;
      if (hx || hy) g.fireObject(o, "Bounce");
    },
    follow_mouse: function (g, o, b, dt) {
      var m = g.input.mouse;
      if (!o.layer.screen_space) m = g.scene.camera.to_world(m[0], m[1]);
      var tx = m[0] - o.width / 2, ty = m[1] - o.height / 2, axis = String(b.axis || "both").toLowerCase();
      if (axis === "x") ty = o.y; else if (axis === "y") tx = o.x;
      var speed = num(b.speed, 0);
      if (speed <= 0) { o.x = tx; o.y = ty; return; }
      var dx = tx - o.x, dy = ty - o.y, dist = Math.hypot(dx, dy);
      if (dist > 0.5) { var step = Math.min(dist, speed * dt); o.x += dx / dist * step; o.y += dy / dist * step; }
    },
    enemy_patrol: function (g, o, b, dt) {
      var st = o._state, speed = num(b.speed, 80), distance = num(b.distance, 160), axis = String(b.axis || "x").toLowerCase();
      if (st.dir === undefined) { st.dir = b.start_left ? -1 : 1; st.origin = axis === "x" ? o.x : o.y; }
      var d = st.dir, pos, turn;
      if (axis === "y") { turn = moveAndCollide(o, 0, d * speed * dt)[1]; pos = o.y; }
      else {
        var gravity = (b.gravity === undefined || b.gravity) ? g.scene.gravity : 0;
        if (gravity) {
          o.vy = Math.min(o.vy + gravity * dt, 900);
          if (moveAndCollide(o, 0, o.vy * dt)[1]) o.vy = 0;
          o.on_ground = standing(o);
        }
        turn = moveAndCollide(o, d * speed * dt, 0)[0]; pos = o.x;
        if (o.on_ground && (b.turn_at_edges === undefined || b.turn_at_edges)) {
          var fx = d > 0 ? o.right + 1 : o.x - 1;
          if (!g.scene.is_solid_at(fx, o.bottom + 2, o)) turn = true;
        }
        o.flip_x = b.flip_reverse ? d > 0 : d < 0;
        autoAnim(o, "walk", "run");
      }
      if (distance > 0 && Math.abs(pos - st.origin) >= distance && (pos - st.origin) * d > 0) turn = true;
      if (turn) st.dir = -d;
      o.vx = axis === "x" ? st.dir * speed : 0;
    },
    solid: function () {},
    collectible: function () {}
  };

  // ==================================================================== game
  function Game(canvas, opts) {
    opts = opts || {};
    this.canvas = canvas; this.ctx = canvas.getContext("2d");
    this.title = opts.title || ""; this.size = opts.width && opts.height ? [opts.width, opts.height] : null;
    this.score = 0; this.lives = 3; this.vars = {};
    this.debug = !!opts.debug; this.input = new Input();
    this.scene = null; this.frame = 0; this.time = 0; this.running = false;
    this.events = []; this.pending = 0; this.imageCache = {}; this._handlers = [];
    this._pendingScene = null; this._touching = {}; this._message = ["", 0]; this._sounds = {}; this._music = null;
    this.error = null; this._loadSeq = 0;
  }
  Game.prototype.invalidateTiles = function () {
    if (this.scene) this.scene.layers.forEach(function (ly) { ly._cache = null; });
  };
  Game.prototype.loadScene = function (name, done) {
    var self = this, data = RadGame.scenes[name];
    var go = function (d) {
      self.scene = new Scene(self, name, d);
      if (self.size) {
        self.scene.view_w = self.size[0]; self.scene.view_h = self.size[1];
        self.scene.world_w = Math.max(self.scene.world_w, self.size[0]); self.scene.world_h = Math.max(self.scene.world_h, self.size[1]);
      }
      self.canvas.width = self.scene.view_w; self.canvas.height = self.scene.view_h;
      document.title = self.title || self.scene.name;
      self._touching = {};
      self.loadCode(name, function () {
        self.inject();
        self.scene.camera.update();
        self.fireScene("Load");
        if (done) done();
      });
    };
    if (data) { go(JSON.parse(JSON.stringify(data))); return; }
    fetch(name + ".scene", { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(name + ".scene: HTTP " + r.status);
      return r.json();
    }).then(go).catch(function (e) { self.fail(e); });
  };
  Game.prototype.loadCode = function (name, done) {
    // the handlers of the previous scene go away, then <name>.js defines the ones of this scene
    var self = this;
    this._handlers.forEach(function (h) { try { global[h] = undefined; } catch (e) { /* read-only */ } });
    this._handlers = [];
    var before = {};
    Object.keys(global).forEach(function (k) { try { if (typeof global[k] === "function") before[k] = true; } catch (e) { /* */ } });
    var s = document.createElement("script");
    s.src = name + ".js?v=" + (++this._loadSeq) + "_" + Date.now();
    s.onload = function () {
      Object.keys(global).forEach(function (k) {
        try { if (typeof global[k] === "function" && !before[k]) self._handlers.push(k); } catch (e) { /* */ }
      });
      done();
    };
    s.onerror = function () { console.warn("radgame: " + name + ".js not found - the scene runs without code"); done(); };
    document.head.appendChild(s);
  };
  Game.prototype.inject = function () {
    var self = this;
    this.scene.all_objects().forEach(function (o) { global[o.name] = o; });
    Object.keys(this.scene.timers).forEach(function (k) { global[k] = self.scene.timers[k]; });
  };
  Game.prototype.handler = function (name) {
    var fn = null;
    try { fn = global[name]; } catch (e) { fn = null; }
    return typeof fn === "function" ? fn : null;
  };
  Game.prototype.call = function (fn, name, args) {
    this.events.push([this.frame, name, args.length]);
    if (this.events.length > 5000) this.events.splice(0, 1000);
    try { return fn.apply(null, args.slice(0, Math.max(fn.length, 0) || args.length)); }
    catch (e) { this.fail(e, name); }
  };
  Game.prototype.fireScene = function (event) {
    var args = Array.prototype.slice.call(arguments, 1), owners = ["Scene", this.scene ? this.scene.name : "", "Game"];
    for (var i = 0; i < owners.length; i++) {
      if (!owners[i]) continue;
      var fn = this.handler(owners[i] + "_" + event);
      if (fn) { this.call(fn, owners[i] + "_" + event, args); return true; }
    }
    return false;
  };
  Game.prototype.fireObject = function (o, event) {
    var args = Array.prototype.slice.call(arguments, 2), done = false, owners = [o.name];
    if (o.group !== o.name) owners.push(o.group);
    for (var i = 0; i < owners.length; i++) {
      var fn = this.handler(owners[i] + "_" + event);
      if (fn) { this.call(fn, owners[i] + "_" + event, args); done = true; }
    }
    return done;
  };
  Game.prototype.fired = function (handler) { return this.events.filter(function (e) { return e[1] === handler; }).length; };
  Game.prototype.fail = function (e, where) {
    var msg = (where ? where + ": " : "") + (e && e.message ? e.message : String(e));
    console.error("radgame error - " + msg + (e && e.stack ? "\n" + e.stack : ""));
    this.error = msg;
  };

  Game.prototype.step = function (dt) {
    var self = this, scene = this.scene;
    if (!scene) return;
    if (dt === undefined) dt = 1 / scene.fps;
    this.processEvents();
    Object.keys(scene.timers).forEach(function (k) {
      var t = scene.timers[k];
      if (t.enabled && t.interval > 0) {
        t._acc += dt * 1000;
        while (t._acc >= t.interval - 1e-6 && t.enabled) {
          t._acc -= t.interval;
          var fn = self.handler(t.name + "_Tick");
          if (fn) self.call(fn, t.name + "_Tick", []);
        }
      }
    });
    scene.live_objects().forEach(function (o) {
      o.behaviours.slice().forEach(function (b) { var f = Behaviours[String(b.type || "")]; if (f) f(self, o, b, dt); });
      o.update_animation(dt);
      if (o.y > scene.world_h + 200 && o.alive && !o.layer.screen_space) {
        if (!self.fireObject(o, "OutOfWorld")) {
          if (ACTOR_BEHAVIOURS.some(function (a) { return o.has(a); })) self.restart_scene(); else o.destroy();
        }
      }
    });
    this.collisions();
    this.fireScene("Update", dt);
    if (this._pendingScene !== null) {
      var name = this._pendingScene; this._pendingScene = null;
      this.running = false;
      this.loadScene(name, function () { self.running = true; });
      this.input.newFrame();
      return;
    }
    this.scene.camera.update();
    this.draw();
    this.input.newFrame();
    this.frame += 1; this.time += dt;
  };
  Game.prototype.processEvents = function () {
    var q = this.input.queue; this.input.queue = [];
    for (var i = 0; i < q.length; i++) {
      var kind = q[i][0], a = q[i][1];
      if (kind === "KeyDown" || kind === "KeyUp") this.fireScene(kind, a[0]);
      else if (kind === "MouseDown") {
        this.fireScene("MouseDown", a[0], a[1], a[2]);
        var w = this.scene.camera.to_world(a[0], a[1]);
        var objs = this.scene.live_objects().sort(function (p, q2) { return q2.z - p.z; });
        for (var j = 0; j < objs.length; j++) {
          var o = objs[j], px = o.layer.screen_space ? a[0] : w[0], py = o.layer.screen_space ? a[1] : w[1];
          if (o.visible && o.contains(px, py)) { this.fireObject(o, "Click"); break; }
        }
      } else if (kind === "MouseUp") this.fireScene("MouseUp", a[0], a[1], a[2]);
    }
  };
  Game.prototype.collisions = function () {
    var objs = this.scene.live_objects().filter(function (o) { return !o.layer.screen_space && o.kind !== "text"; });
    var now = {}, pairs = [], i, j, objects = this.scene.objects;
    for (i = 0; i < objs.length; i++) {
      var ra = objs[i].rect;
      for (j = i + 1; j < objs.length; j++) {
        if (hit(ra, objs[j].rect)) {
          var key = objs[i].name < objs[j].name ? objs[i].name + "\u0001" + objs[j].name : objs[j].name + "\u0001" + objs[i].name;
          now[key] = true;
        }
      }
    }
    Object.keys(now).sort().forEach(function (k) { if (!this._touching[k]) pairs.push(k); }, this);
    var isActor = function (o) { return ACTOR_BEHAVIOURS.some(function (x) { return o.has(x); }); };
    for (i = 0; i < pairs.length; i++) {
      var p = pairs[i].split("\u0001"), a = objects[p[0]], b = objects[p[1]];
      if (!a || !b || !a.alive || !b.alive) continue;
      [[a, b], [b, a]].forEach(function (ab) {
        var coll = ab[1].behaviour("collectible");
        if (coll && isActor(ab[0]) && ab[1].alive) {
          this.score += Math.round(num(coll.score, 1));
          if (coll.sound) this.play_sound(coll.sound);
        }
      }, this);
      this.fireObject(a, "Collide", b);
      this.fireObject(b, "Collide", a);
      [[a, b], [b, a]].forEach(function (ab) { if (ab[1].has("collectible") && isActor(ab[0])) ab[1].destroy(); });
    }
    var keep = {};
    Object.keys(now).forEach(function (k) {
      var q = k.split("\u0001");
      if (objects[q[0]] && objects[q[0]].alive && objects[q[1]] && objects[q[1]].alive) keep[k] = true;
    });
    this._touching = keep;
  };
  Game.prototype.clampToWorld = function (o) {
    var s = this.scene;
    o.x = Math.max(0, Math.min(o.x, s.world_w - o.width)); o.y = Math.max(0, Math.min(o.y, s.world_h - o.height));
  };
  Game.prototype.draw = function () {
    var ctx = this.ctx, s = this.scene, bg = s.background;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (typeof bg === "string" && s.images[bg] && s.images[bg].naturalWidth) ctx.drawImage(s.images[bg], 0, 0, this.canvas.width, this.canvas.height);
    else { ctx.fillStyle = bg || "#6EC1E4"; ctx.fillRect(0, 0, this.canvas.width, this.canvas.height); }
    var ox = s.camera.x, oy = s.camera.y;
    for (var i = 0; i < s.layers.length; i++) s.layers[i].draw(ctx, ox, oy);
    this.fireScene("Draw", ctx);
    var text = this._message[0];
    if (text && this.time < this._message[1]) this.banner(text, "#000000", "#FFFFFF");
    if (this.error) this.banner("Error: " + this.error, "#8B0000", "#FFFFFF", 18);
  };
  Game.prototype.banner = function (text, bg, fg, size) {
    var ctx = this.ctx, px = size || 34;
    ctx.font = "bold " + px + "px Segoe UI, Arial, sans-serif"; ctx.textBaseline = "middle";
    var w = Math.min(this.canvas.width - 8, ctx.measureText(text).width + 32), h = px + 20;
    var x = (this.canvas.width - w) / 2, y = (this.canvas.height - h) / 2;
    ctx.fillStyle = bg; ctx.fillRect(x, y, w, h);
    ctx.fillStyle = fg; ctx.textAlign = "center"; ctx.fillText(text, this.canvas.width / 2, y + h / 2, w - 16);
    ctx.textAlign = "left";
  };

  Game.prototype.attachInput = function () {
    var self = this, cv = this.canvas;
    var prevent = { left: 1, right: 1, up: 1, down: 1, space: 1 };
    global.addEventListener("keydown", function (e) {
      var k = keyName(e); if (prevent[k]) e.preventDefault();
      if (!e.repeat) self.input.press(k);
    });
    global.addEventListener("keyup", function (e) { self.input.release(keyName(e)); });
    global.addEventListener("blur", function () { Object.keys(self.input.held).forEach(function (k) { self.input.release(k); }); });
    var pos = function (e) {
      var r = cv.getBoundingClientRect();
      return [Math.round((e.clientX - r.left) * cv.width / (r.width || 1)), Math.round((e.clientY - r.top) * cv.height / (r.height || 1))];
    };
    cv.addEventListener("mousemove", function (e) { self.input.mouse = pos(e); });
    cv.addEventListener("mousedown", function (e) {
      var p = pos(e), b = e.button + 1; self.input.mouse = p; self.input.buttons[b] = true;
      self.input.queue.push(["MouseDown", [p[0], p[1], b]]); cv.focus();
    });
    cv.addEventListener("mouseup", function (e) {
      var p = pos(e), b = e.button + 1; delete self.input.buttons[b];
      self.input.queue.push(["MouseUp", [p[0], p[1], b]]);
    });
  };
  Game.prototype.run = function (sceneName) {
    var self = this, params = new URLSearchParams(location.search);
    var frames = parseInt(params.get("frames") || "0", 10), fixed = !!params.get("fixed"), last = null;
    this.attachInput();
    this.loadScene(sceneName, function () {
      self.running = true;
      var tick = function (ts) {
        if (self.stopped) return;
        if (self.running && self.scene) {
          var dt = fixed || last === null ? 1 / self.scene.fps : Math.min((ts - last) / 1000, 0.05);
          last = ts;
          try { self.step(dt); } catch (e) { self.fail(e); self.draw(); }
          if (frames && self.frame >= frames) { self.stopped = true; return; }
        } else last = null;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  };

  // ---- helpers used by the user code
  Game.prototype.go_to_scene = function (name) { this._pendingScene = String(name); };
  Game.prototype.restart_scene = function () { this._pendingScene = this.scene.name; };
  Game.prototype.quit = function () { this.stopped = true; this.running = false; this.banner("Game over", "#000000", "#FFFFFF"); };
  Game.prototype.play_sound = function (id) {
    var path = (this.scene && this.scene.sounds[id]) || id;
    try {
      var a = this._sounds[path] || (this._sounds[path] = new Audio(path));
      var c = a.cloneNode(); var p = c.play(); if (p && p.catch) p.catch(function () {});
    } catch (e) { /* no audio */ }
  };
  Game.prototype.play_music = function (id, loop) {
    this.stop_music();
    try {
      this._music = new Audio((this.scene && this.scene.sounds[id]) || id);
      this._music.loop = loop === undefined ? true : !!loop;
      var p = this._music.play(); if (p && p.catch) p.catch(function () {});
    } catch (e) { /* no audio */ }
  };
  Game.prototype.stop_music = function () { if (this._music) { this._music.pause(); this._music = null; } };
  Game.prototype.show_message = function (text, seconds) { this._message = [String(text), this.time + (seconds === undefined ? 2 : seconds)]; };

  // ==================================================================== public API + VB-style helpers
  var current = null;
  var RadGame = {
    VERSION: VERSION, scenes: {}, Game: Game, Scene: Scene, Sprite: Sprite, TextObject: TextObject, Area: Area,
    Layer: Layer, Timer: Timer, Input: Input, Behaviours: Behaviours, moveAndCollide: moveAndCollide,
    get game() { return current; },
    addScene: function (data) { if (data && data.name) RadGame.scenes[data.name] = data; },
    run: function (sceneName, opts) {
      opts = opts || {};
      var cv = opts.canvas || document.getElementById(opts.canvasId || "game");
      if (!cv) { cv = document.createElement("canvas"); cv.id = "game"; document.body.appendChild(cv); }
      cv.tabIndex = 0;
      current = new Game(cv, opts);
      current.run(sceneName || Object.keys(RadGame.scenes)[0]);
      try { cv.focus(); } catch (e) { /* */ }
      return current;
    },
    /** tests: run n frames now (dt = 1/fps) */
    stepFrames: function (n) { for (var i = 0; i < (n || 1); i++) current.step(); return current.frame; }
  };
  global.RadGame = RadGame;
  Object.defineProperty(global, "game", { get: function () { return current; }, configurable: true });
  global.GoToScene = function (name) { current.go_to_scene(name); };
  global.RestartScene = function () { current.restart_scene(); };
  global.Quit = function () { current.quit(); };
  global.AddScore = function (n) { current.score += Math.round(n === undefined ? 1 : n); };
  global.PlaySound = function (id) { current.play_sound(id); };
  global.PlayMusic = function (id, loop) { current.play_music(id, loop); };
  global.StopMusic = function () { current.stop_music(); };
  global.ShowMessage = function (text, seconds) { current.show_message(text, seconds); };
  global.IsKeyDown = function (key) { return current.input.down(key); };
  global.Find = function (name) { return current.scene.objects[name] || null; };
  global.FindGroup = function (group) { return current.scene.live_objects().filter(function (o) { return o.group === group; }); };
  global.Clone = function (obj, x, y) {
    var d = { name: obj.name, kind: obj.kind, x: x === undefined ? obj.x : x, y: y === undefined ? obj.y : y, w: obj.w, h: obj.h,
      scale: obj.scale, rotation: obj.rotation, z: obj.z, props: Object.assign({}, obj.props),
      behaviours: obj.behaviours.map(function (b) { return Object.assign({}, b); }) };
    if (obj instanceof Sprite) { d.image = obj.image_id; d.spritesheet = obj.sheet_id; d.animation = obj.animation; }
    if (obj instanceof TextObject) d.text = obj.text;
    var n = current.scene.add_object(d, obj.layer); n.group = obj.group; global[n.name] = n;
    return n;
  };
  global.AddTimer = function (name, interval, enabled) {
    var t = current.scene.timers[name] = new Timer(name, interval === undefined ? 1000 : interval, enabled);
    global[name] = t; return t;
  };
  global.Random = function (a, b) { return a + Math.floor(Math.random() * (b - a + 1)); };
})(window);
