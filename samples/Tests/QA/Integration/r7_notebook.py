import os, shutil, time
os.environ.setdefault("QA_NAME", "qa7nb")
from qh import *  # noqa
from pathlib import Path
d = Path(WORK) / "nb"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
w = window()
nf = getattr(w, "notebook_feature", None)
check("notebook feature installed", nf is not None)
v = nf.new_notebook("datascience", d / "Analysis.ipynb")
check("starter notebook opened as tab", v is not None and w.tabs.indexOf(v) >= 0)
check("Notebook menu visible when notebook tab active", wait(lambda: nf.menu.menuAction().isVisible(), 5))
wait(lambda: v.is_ready(), 40)
check("notebook page ready", v.is_ready())
v.run_all()
ok = wait(lambda: v.kernel is not None and v.kernel.alive() and not v.busy(), 180)
check("run all finished", ok)
outs = [o for c in v.notebook.cells if c.cell_type == "code" for o in c.outputs]
mimes = {k for o in outs for k in (o.get("data") or {}).keys()}
check("text/html (table) output", "text/html" in mimes, mimes)
check("image/png (plot) output", "image/png" in mimes, mimes)
check("no error outputs in starter", not [o for o in outs if o.get("output_type") == "error"], outs[:3])
pump(1.5); shot(w, "notebook_runall")
# error + interrupt
c = v.add_cell("code"); v.set_source(c.id if hasattr(c, "id") else c, "{}['missing']")
cid = c.id if hasattr(c, "id") else c
v.run_cell(cid); wait(lambda: not v.busy(), 30)
err = [o for o in v.notebook.cell(cid).outputs if o.get("output_type") == "error"]
check("KeyError traceback shown", err and err[0].get("ename") == "KeyError", v.notebook.cell(cid).outputs)
c2 = v.add_cell("code"); cid2 = c2.id if hasattr(c2, "id") else c2
v.set_source(cid2, "import time\nfor i in range(600): time.sleep(0.1)")
v.run_cell(cid2); pump(1.5); t0 = time.time(); v.interrupt()
wait(lambda: not v.busy(), 20)
err2 = [o for o in v.notebook.cell(cid2).outputs if o.get("output_type") == "error"]
check("interrupt -> KeyboardInterrupt", err2 and err2[0].get("ename") == "KeyboardInterrupt", v.notebook.cell(cid2).outputs)
print("interrupt took %.2fs" % (time.time() - t0))
check("variables window lists df", wait(lambda: any(getattr(x, "name", None) == "df" or (isinstance(x, (list, tuple, dict)) and "df" in str(x)[:40]) for x in v.variables), 10), str(v.variables)[:300])
check("save", v.save())
from radide.notebook.model import Notebook
nb2 = Notebook.load(d / "Analysis.ipynb")
check("nbformat validation of saved file", nb2.validate() is None, nb2.validate())
m2 = {k for c in nb2.cells for o in c.outputs for k in (o.get("data") or {})}
check("outputs kept after reload", "image/png" in m2 and "text/html" in m2, m2)
v.restart(ask=False); wait(lambda: v.kernel is not None and v.kernel.status == "idle", 60)
c3 = v.add_cell("code"); cid3 = c3.id if hasattr(c3, "id") else c3
v.set_source(cid3, "print('df' in dir())"); v.run_cell(cid3); wait(lambda: not v.busy(), 30)
txt = "".join(o.get("text", "") for o in v.notebook.cell(cid3).outputs)
check("restart cleared state", "False" in txt, v.notebook.cell(cid3).outputs)
v.export_py = getattr(v, "export_py")
py = nb2.to_py(); check("export to # %% script", "# %%" in py)
# close the tab -> kernel stops
k = v.kernel
v.set_modified(False)
w.tabs.tabCloseRequested.emit(w.tabs.indexOf(v)); pump(2)
check("closing tab stops kernel", k is None or not k.alive())
finish(w)
