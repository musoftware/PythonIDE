# JsDebug_StaticSite

**static-web** - client-side JavaScript debugging in the Preview (QtWebEngine DevTools port + vscode-js-debug in
`pwa-chrome` attach mode).

**Try it:** open, F9 on line 3 (`const sum = a + b;`) and line 15 of `app.js`, press F5. The debugger stops on
line 15 while the page loads (the Preview reloads once the debugger is attached), F5 continues; click **Add**
in the Preview - it stops in `add()` with `a`, `b` in Locals; type `a * 10 + b` in Immediate.
Needs Node.js (for the adapter; js-debug is downloaded into %LOCALAPPDATA%\RADIDE\tools on first use).
