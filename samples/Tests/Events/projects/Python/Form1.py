"""EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)."""
import os

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


def evlog(name, rest=""):
    p = os.environ.get("RADEVT_LOG")
    if not p:
        return
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"EVT {name}{' ' + rest if rest else ''}\n")


def raw(e):
    return f"{e.X} {e.Y} {e.Button} {e.KeyCode} {e.KeyChar}".strip()


class Form1(Form1Designer):
    closing = 0

    def Form1_Load(self, *_):
        evlog("Form1_Load")

    def Form1_Activated(self, *_):
        evlog("Form1_Activated")

    def Form1_FormClosed(self, *_):
        evlog("Form1_FormClosed")

    def cmdA_MouseDown(self, e):
        evlog("cmdA_MouseDown", raw(e))

    def cmdA_MouseUp(self, e):
        evlog("cmdA_MouseUp", raw(e))

    def cmdA_Click(self, *_):
        evlog("cmdA_Click")

    def lblA_MouseDown(self, e):
        evlog("lblA_MouseDown", raw(e))

    def lblA_MouseUp(self, e):
        evlog("lblA_MouseUp", raw(e))

    def lblA_Click(self, *_):
        evlog("lblA_Click")

    def txtA_GotFocus(self, *_):
        evlog("txtA_GotFocus")

    def txtA_LostFocus(self, *_):
        evlog("txtA_LostFocus")

    def txtA_KeyDown(self, e):
        evlog("txtA_KeyDown", raw(e))

    def txtA_KeyPress(self, e):
        evlog("txtA_KeyPress", raw(e))

    def txtA_KeyUp(self, e):
        evlog("txtA_KeyUp", raw(e))

    def txtA_TextChanged(self, *_):
        evlog("txtA_TextChanged", f"text={self.txtA_var.get()}")

    def txtB_GotFocus(self, *_):
        evlog("txtB_GotFocus")

    def txtB_LostFocus(self, *_):
        evlog("txtB_LostFocus")

    def chkA_CheckedChanged(self, *_):
        evlog("chkA_CheckedChanged", f"value={int(self.chkA_var.get())}")

    def lstA_SelectedIndexChanged(self, *_):
        evlog("lstA_SelectedIndexChanged", f"index={(self.lstA.curselection() or (-1,))[0]}")

    def Form1_FormClosing(self, e):
        Form1.closing += 1
        evlog("Form1_FormClosing")
        if Form1.closing == 1:
            e.Cancel = True

    def cmdCode_Click(self):
        evlog("cmdCode_Click", "begin")
        self.txtA_var.set("code")
        self.chkA_var.set(True)
        self.lstA.selection_clear(0, "end")
        self.lstA.selection_set(2)
        evlog("cmdCode_Click", "end")

    def cmdTmr_Click(self):
        evlog("cmdTmr_Click")
        self.tmrA.Enabled = True

    def tmrA_Tick(self):
        self.tmrA.Enabled = False
        evlog("tmrA_Tick")


if __name__ == "__main__":
    Form1().show()
