"""Ring applications without forms - New Project > Ring > "Ring (Console / Web / Library)".

Templates:
  console   a console program (main.ring + a func main), output in the Output window
  web       a web application served by RingHTTPLib (load "httplib.ring": cpp-httplib, shipped with Ring):
            routes, an HTML page from templates/index.html, a JSON API and a form POST
  library   a Ring library (mylib.ring: functions + a class) and a test program that loads it
  weblib    a WebLib page (load "weblib.ring") rendered to an HTML file - the Ring web framework's
            page classes without a web server

The project runs its startup .ring file (``ring main.ring``) like a Ring script project; F5 debugs with the
Ring agent, IntelliSense / F1 / Error List come from RingQtPlugin (radide/languages/ring_intel.py).
"""
from __future__ import annotations

from pathlib import Path

from ..model import Project
from .ring_script import RingScriptPlugin

TEMPLATES = [
    ("console", "Console Application (Ring)",
     "A Ring console program: main.ring with func main. Output appears in the Output window.", "SP_ComputerIcon"),
    ("web", "Web Application (Ring HTTPLib)",
     "A web server written in Ring with RingHTTPLib (cpp-httplib): routes, an HTML page, a JSON API and a "
     "form. Run it and open http://localhost:8080.", "SP_DriveNetIcon"),
    ("library", "Ring Library",
     "A reusable Ring library (functions and a class in its own .ring file) and a test program that loads it.",
     "SP_DirIcon"),
    ("weblib", "WebLib Page Generator (Ring)",
     "Builds an HTML page with Ring's WebLib page classes (load \"weblib.ring\") and opens it in the browser.",
     "SP_FileDialogDetailedView"),
]

_CONSOLE = '''# {name} - a Ring console application
# Output appears in the Output window. F5 debugs (breakpoints, stepping, locals).

load "stdlib.ring"

func main
    see "Hello from {name}!" + nl
    cName = "Ring"
    see "Welcome to " + cName + " " + version() + nl

    aNumbers = [5, 3, 8, 1]
    see "Sorted: " + joinList(sort(aNumbers), ", ") + nl
    see "Sum: " + sumOf(aNumbers) + nl

func joinList aList, cSep
    cOut = ""
    for i = 1 to len(aList)
        if i > 1 cOut += cSep ok
        cOut += aList[i]
    next
    return cOut

func sumOf aList
    nSum = 0
    for x in aList
        nSum += x
    next
    return nSum
'''

_WEB = '''# {name} - a web application written in Ring (RingHTTPLib)
# Run (F5 / Ctrl+F5) and open http://localhost:{port} in the browser. Stop with Debug > Stop.

load "httplib.ring"
load "stdlib.ring"

nPort = {port}
aMessages = []

oServer = new Server {{
    route(:Get, "/", :pageHome)
    route(:Get, "/api/hello", :apiHello)
    route(:Post, "/messages", :postMessage)
    ? "Listening on http://localhost:" + nPort
    listen("0.0.0.0", nPort)
}}

func pageHome
    cHtml = read("templates/index.html")
    cList = ""
    for cMsg in aMessages
        cList += "<li>" + htmlEncode(cMsg) + "</li>"
    next
    cHtml = substr(cHtml, "{{messages}}", cList)
    oServer.setContent(cHtml, "text/html")

func apiHello
    oServer.setContent('{{"message": "Hello from Ring", "count": ' + len(aMessages) + '}}', "application/json")

func postMessage
    cText = oServer["text"]            # a form field (oServer.variable("text") does the same)
    if trim(cText) != ""
        aMessages + cText
    ok
    pageHome()

func htmlEncode cText
    cText = substr(cText, "&", "&amp;")
    cText = substr(cText, "<", "&lt;")
    cText = substr(cText, ">", "&gt;")
    return cText
'''

_WEB_HTML = '''<!doctype html>
<html>
<head><meta charset="utf-8"><title>{name}</title>
<style>body{{font-family:Segoe UI,Arial;margin:40px;max-width:640px}} input{{padding:6px;width:70%}}
button{{padding:6px 14px}}</style></head>
<body>
<h1>{name}</h1>
<p>Served by Ring (RingHTTPLib). JSON API: <a href="/api/hello">/api/hello</a></p>
<form method="post" action="/messages">
  <input name="text" placeholder="Write a message"> <button>Send</button>
</form>
<ul>{{messages}}</ul>
</body>
</html>
'''

_LIB = '''# {lib} - a Ring library
# Other programs use it with:  load "{lib}.ring"

func addNumbers nA, nB
    # Returns the sum of two numbers
    return nA + nB

func repeatText cText, nTimes
    # Returns cText repeated nTimes
    cOut = ""
    for i = 1 to nTimes
        cOut += cText
    next
    return cOut

class Counter
    nValue = 0
    cName = "counter"

    func init cCounterName
        cName = cCounterName
        return self

    func increment
        nValue++
        return nValue

    func reset
        nValue = 0

    func show
        see cName + " = " + nValue + nl
'''

_LIB_TEST = '''# Tests of {lib}.ring - run this file (it is the startup file)

load "{lib}.ring"

func main
    check("addNumbers", addNumbers(2, 3) = 5)
    check("repeatText", repeatText("ab", 3) = "ababab")
    oCounter = new Counter("clicks")
    oCounter.increment()
    oCounter.increment()
    check("Counter", oCounter.nValue = 2)
    oCounter.show()

func check cName, lOk
    if lOk
        see "PASS " + cName + nl
    else
        see "FAIL " + cName + nl
    ok
'''

_WEBLIB = '''# {name} - builds an HTML page with WebLib (Ring's web library) and opens it

load "weblib.ring"
import System.Web

func main
    aRows = [["Language", "Ring"], ["Library", "WebLib"], ["Version", version()]]
    oPage = new HTMLPageFunctions {{
        boxstart()
            text("Hello from Ring WebLib")
            newline()
        boxend()
        divstart([:style = styleWidth("500px")])
            newline()
            text("This page was generated by {name}, a Ring program.")
            newline() newline()
            for aRow in aRows
                text(aRow[1] + " : " + aRow[2])
                newline()
            next
        divend()
    }}
    cFile = currentdir() + "/page.html"
    write(cFile, oPage.output())
    see "Written: " + cFile + nl
    system('start "" "' + cFile + '"')
'''


class RingAppPlugin(RingScriptPlugin):
    id = "ring-app"
    display_name = "Ring (Console / Web / Library)"
    foreign_only = False
    project_name_base = "RingApp"

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        template = template or "console"
        files: dict[str, str]
        startup = "main"
        if template == "web":
            files = {"main.ring": _WEB.format(name=name, port=8080),
                     "templates/index.html": _WEB_HTML.format(name=name)}
        elif template == "library":
            lib = (name[:1].lower() + name[1:]) if name else "mylib"
            files = {f"{lib}.ring": _LIB.format(lib=lib), "test.ring": _LIB_TEST.format(lib=lib)}
            startup = "test"
        elif template == "weblib":
            files = {"main.ring": _WEBLIB.format(name=name)}
        else:
            files = {"main.ring": _CONSOLE.format(name=name)}
        for rel, text in files.items():
            p = folder / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(text, encoding="utf-8")
        modules = [r for r in files if r.endswith(".ring")]
        project = Project(folder, name, self.id, [], startup, modules)
        project.save()
        return project


PLUGIN = RingAppPlugin()
