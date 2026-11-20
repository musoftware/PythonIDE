# Frontend_React_Vite

**node-web + Vite (React 19)** - made with *Site > New Front-end App > React (Vite)* (`npm create vite@latest`,
template `react`).

Tests: the dev server (`npm run dev`) behind the IDE's DevServer and Preview (HMR passes through), JavaScript
debugging of the app in the Preview with source maps, and *Site > Build Production*.

**Try it:** open `project.radproj`. The first F5 runs `npm install` (node_modules is not kept in the sample).
Set a breakpoint (F9) in `src/App.jsx` on the `onClick={() => setCount(...)}` line, press F5, click the
**Count is** button in the Preview - the IDE stops in App.jsx (Locals, Call Stack, F10, Immediate).
*Site > Build Production* writes `dist/`.

Needs Node.js 20.19+ / 22.12+.
