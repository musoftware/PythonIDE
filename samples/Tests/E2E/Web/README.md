# Web journeys - the "RAD Store" built in every web stack

Each journey builds the same small product - **RAD Store** - with one web stack, entirely through the IDE the way a
user does, and checks every step (PASS / FAIL / SKIP, screenshots):

home page designed in the **Design View** (GrapesJS) - product list from **SQLite** set up in the **Databases**
workspace - add / edit / delete with validation (the pages' own forms, hidden CSRF fields kept) - **login**
(`admin` / `secret`) - an **Arabic RTL** page - a **JSON API** (`/api/products`) - CSS / JS assets - the dev
server and the **Preview** (QtWebEngine DOM checks, phone / tablet sizes) - a **breakpoint** hit by a request -
**IntelliSense** (the language, HTML tags, CSS properties in Monaco) - **Site > Publish** to a local folder and to
a local **FTP** server (pyftpdlib, started by the test on 127.0.0.1) - the **published copy runs** on its own and
answers the same pages.

| File | What |
|---|---|
| `journey_web.py <stack>` | the journey, in-process (the real `MainWindow`, offscreen): 17 steps |
| `stacks/<stack>.py` | the stack: New Project language + template, the store's source files, routes, schema / seed SQL, debug / IntelliSense probes, how the published copy runs |
| `run_web.py [stack ...]` | runs the journeys one by one, writes `web_matrix.md` / `web_matrix.json` (journeys x steps) |
| `journey_web_frozen.py` | the same flow against the **frozen RADIDE.exe** through the automation channel (`radide/automation/commands_web.py`): php, static, node, flask, fastapi |
| `webcheck.py` | the HTTP checks used by the frozen journey |
| `Projects/` | the RAD Store projects the journeys built (PhpStore, StaticStore, NodeStore, FlaskStore, DjangoStore, FastApiStore, AspStore, SpringStore, NestStore, RailsStore, CiStore) without `.venv` / `node_modules` / `vendor` / databases / build output - open one with File > Open Project; Ctrl+F5 recreates what is missing (CodeIgniter: `composer install` first) |

Stacks: `php` (PHP Empty Site, PDO SQLite), `static` (HTML Bootstrap Site; the catalogue is a JSON file rendered by
the page; JavaScript debugged in the Preview), `node` (Express + `node:sqlite`), `flask`, `django` (Django panel:
makemigrations / migrate / createsuperuser), `fastapi`, `aspnet` (minimal APIs + Microsoft.Data.Sqlite), `spring`
(Spring Boot MVC + Thymeleaf + sqlite-jdbc), `nestjs`, `rails`, `codeigniter`, `laravel`. A stack whose toolchain
is missing SKIPs every step with the reason.

## Running

```bat
set E2E_OUT=%TEMP%\radide-e2e
.venv\Scripts\python samples\Tests\E2E\Web\journey_web.py php
.venv\Scripts\python samples\Tests\E2E\Web\run_web.py php static node flask django fastapi
:: one or two steps of the last run again (reuses its project): E2E_ONLY=run,debug
set E2E_ONLY=run,debug & .venv\Scripts\python samples\Tests\E2E\Web\journey_web.py django
:: the frozen build (portable copy, hidden desktop)
.venv\Scripts\python samples\Tests\E2E\Web\journey_web_frozen.py %TEMP%\e2e\web --onedir <build>\dist\RADIDE
```

Output: `%E2E_OUT%\Web-<stack>\results.json`, `shots\*.png` (IDE widgets via `widget.grab()`, the Preview via
`QWebEngineView.grab()`), `work\` (the project, published copies, server logs). `E2E_DAP_TRACE=1` writes the DAP
events of the debug step to `work\dap_trace.log`. Rails needs a short `E2E_OUT` (gem builds fail under MAX_PATH).

Environment (set by the harness, `samples/Tests/E2E/e2e_lib.py`): offscreen Qt, `QT_QPA_FONTDIR`,
`RADIDE_NO_BROWSER=1`, WebEngine without GPU, own QSettings organisation `RADIDE-TEST-E2EWEB`; servers bind to
127.0.0.1 only; only processes the journey started are stopped.
