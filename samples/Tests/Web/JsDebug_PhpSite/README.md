# JsDebug_PhpSite

**php-web** - PHP (Xdebug) and the page's JavaScript debugged in **one** F5 session.

**Try it:** open, F9 on line 3 of `index.php` and on lines 3 and 15 of `app.js`, press F5. The server stops in
`index.php` first (Xdebug), then the Preview stops in `app.js` (page load); click **Add** to stop in `add()`.
Every page request runs PHP again, so the PHP breakpoint hits again on each reload.
Needs PHP + Node.js (Xdebug / php-debug / js-debug are downloaded on first use).
