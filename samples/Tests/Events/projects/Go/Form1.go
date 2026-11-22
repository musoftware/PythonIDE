// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
package main

import (
	"fmt"
	"os"
)

var closing = 0

func evlog(name, rest string) {
	p := os.Getenv("RADEVT_LOG")
	if p == "" {
		return
	}
	f, err := os.OpenFile(p, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	if rest != "" {
		rest = " " + rest
	}
	fmt.Fprintf(f, "EVT %s%s\n", name, rest)
	f.Close()
}

func Form1_Load(e RadEvent) {
	evlog("Form1_Load", "")
}

func Form1_Activated(e RadEvent) {
	evlog("Form1_Activated", "")
}

func Form1_FormClosed(e RadEvent) {
	evlog("Form1_FormClosed", "")
}

func cmdA_MouseDown(e RadEvent) {
	evlog("cmdA_MouseDown", e.Args)
}

func cmdA_MouseUp(e RadEvent) {
	evlog("cmdA_MouseUp", e.Args)
}

func cmdA_Click(e RadEvent) {
	evlog("cmdA_Click", "")
}

func lblA_MouseDown(e RadEvent) {
	evlog("lblA_MouseDown", e.Args)
}

func lblA_MouseUp(e RadEvent) {
	evlog("lblA_MouseUp", e.Args)
}

func lblA_Click(e RadEvent) {
	evlog("lblA_Click", "")
}

func txtA_GotFocus(e RadEvent) {
	evlog("txtA_GotFocus", "")
}

func txtA_LostFocus(e RadEvent) {
	evlog("txtA_LostFocus", "")
}

func txtA_KeyDown(e RadEvent) {
	evlog("txtA_KeyDown", e.Args)
}

func txtA_KeyPress(e RadEvent) {
	evlog("txtA_KeyPress", e.Args)
}

func txtA_KeyUp(e RadEvent) {
	evlog("txtA_KeyUp", e.Args)
}

func txtA_TextChanged(e RadEvent) {
	evlog("txtA_TextChanged", "text="+Get("txtA", "Text"))
}

func txtB_GotFocus(e RadEvent) {
	evlog("txtB_GotFocus", "")
}

func txtB_LostFocus(e RadEvent) {
	evlog("txtB_LostFocus", "")
}

func chkA_CheckedChanged(e RadEvent) {
	evlog("chkA_CheckedChanged", "value="+Get("chkA", "Value"))
}

func lstA_SelectedIndexChanged(e RadEvent) {
	evlog("lstA_SelectedIndexChanged", "index="+Get("lstA", "ListIndex"))
}

func Form1_FormClosing(e RadEvent) {
	closing++
	evlog("Form1_FormClosing", "")
	if closing == 1 {
		Set("Form1", "Cancel", "True")
	}
}

func cmdCode_Click(e RadEvent) {
	evlog("cmdCode_Click", "begin")
	Set("txtA", "Text", "code")
	Set("chkA", "Value", 1)
	Set("lstA", "ListIndex", 2)
	evlog("cmdCode_Click", "end")
}

func cmdTmr_Click(e RadEvent) {
	evlog("cmdTmr_Click", "")
	Set("tmrA", "Enabled", "True")
}

func tmrA_Tick(e RadEvent) {
	Set("tmrA", "Enabled", "False")
	evlog("tmrA_Tick", "")
}
