"""Run the assembly form project in the GUI Bridge host (radide.runtimes.bridge), click the button, read the
label back from the real window and save a picture of the form."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))      # the RAD IDE folder
from radide.languages import get_plugin
from radide.model import Project
from radide.runtimes.bridge import BridgeRuntime

folder = Path(sys.argv[1])
plugin = get_plugin("asm-nasm")
project = Project.load(folder)
handlers = set(plugin.handlers_in_project(folder, project))
print("handlers:", sorted(handlers))
rt = BridgeRuntime(folder, [str(folder / "_radapp.exe")], handlers)
rt.load()
rt.start_program()
vf = rt.forms["form1"]
rt.startup_form = vf
vf.load()
vf.vb_call("show", [])
root = rt.root
root.update()


def text(name):
    return str(vf.vb_get(name.lower()).vb_get("text"))


print("after Load:", text("lblMessage"))
ok = text("lblMessage").startswith("Hello from assembly!")
rt.event("btnAdd", "Click")
root.update()
print("after click: txtNumber =", text("txtNumber"), " lblClicks =", text("lblClicks"), " lblMessage =", text("lblMessage"))
ok &= text("txtNumber") == "42" and text("lblClicks") == "1" and text("lblMessage") == "The assembly handler added 1."
print("RESULT", "OK" if ok else "FAIL", flush=True)
rt.end()
