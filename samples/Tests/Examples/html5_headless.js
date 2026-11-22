// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Runs an HTML5 game project (radgame.js + scenes.js + <Scene>.js) in Node.js without a browser: a tiny fake DOM
// (canvas 2D context that draws nothing, document, localStorage), then N frames with scripted keys.
//
//   node html5_headless.js <project folder> <scene> <frames> [key:from-to,...]
//
// Prints the console.log lines of the game and finally "html5-test: frames=<n> score=<s> lives=<l> objects=<k>".
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [folder, sceneName, framesArg, keysArg] = process.argv.slice(2);
const frames = parseInt(framesArg || "120", 10);
const script = (keysArg || "").split(",").filter(Boolean).map((p) => {
    const [k, span] = p.split(":");
    const [a, b] = span.split("-").map(Number);
    return { k, a, b };
});

const noop = () => {};
const ctx2d = new Proxy({}, {
    get: (t, name) => (name === "measureText" ? () => ({ width: 10 }) :
        name === "createLinearGradient" || name === "createPattern" ? () => ({ addColorStop: noop }) :
        name === "getImageData" ? () => ({ data: [] }) : (name in t ? t[name] : noop)),
    set: (t, name, v) => { t[name] = v; return true; },
});
function element(tag) {
    return {
        tagName: tag, style: {}, width: 800, height: 600, children: [], tabIndex: 0,
        getContext: () => ctx2d, addEventListener: noop, focus: noop, remove: noop,
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
        appendChild(c) { this.children.push(c); return c; },
    };
}
const store = {};
const sandbox = {
    console, Math, Date, JSON, setTimeout, clearTimeout, setInterval, clearInterval,
    URLSearchParams, Promise,
    location: { search: "?fixed=1" },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
                    removeItem: (k) => { delete store[k]; } },
    requestAnimationFrame: noop,            // frames are stepped below
    addEventListener: noop,
    Image: function () { this.complete = true; this.naturalWidth = 0; },
    Audio: function () { this.play = () => Promise.resolve(); this.pause = noop; this.cloneNode = () => this; },
    fetch: () => Promise.reject(new Error("no fetch in the headless runner")),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const canvas = element("canvas");
sandbox.document = {
    title: "",
    getElementById: (id) => (id === "game" ? canvas : null),
    createElement: (tag) => element(tag),
    body: element("body"),
    head: {
        appendChild(s) {                      // <script src="Scene.js?v=..."> - run it now, then onload
            const file = path.join(folder, String(s.src).split("?")[0]);
            try {
                vm.runInContext(fs.readFileSync(file, "utf8"), sandbox, { filename: file });
                if (s.onload) s.onload();
            } catch (e) {
                console.log("html5-test: script error " + e.stack);
                if (s.onerror) s.onerror(e);
            }
            return s;
        },
    },
};
vm.createContext(sandbox);
for (const f of ["radgame.js", "scenes.js"]) {
    vm.runInContext(fs.readFileSync(path.join(folder, f), "utf8"), sandbox, { filename: f });
}
const RadGame = sandbox.RadGame;
RadGame.run(sceneName, { title: "headless" });
const game = RadGame.game;
if (game.error) console.log("html5-test: error " + game.error);
for (let n = 0; n < frames; n++) {
    for (const s of script) {
        if (n === s.a) game.input.press(s.k);
        else if (n === s.b) game.input.release(s.k);
    }
    game.step(1 / 60);
    if (game.error) { console.log("html5-test: error " + game.error); break; }
}
const objects = game.scene ? game.scene.live_objects().length : 0;
console.log(`html5-test: frames=${game.frame} score=${game.score} lives=${game.lives} objects=${objects}` +
            ` error=${game.error || ""}`);
