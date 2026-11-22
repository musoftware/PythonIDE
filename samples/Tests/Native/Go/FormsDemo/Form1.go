// Event handlers for Form1 - written for the GUI Bridge (radlib.go); the native build compiles the same
// code against radforms (cgo). Handlers: func <Control>_<Event>() or func <Control>_<Event>(e RadEvent).
package main

import "fmt"

var ticks = 0

func Form1_Load(e RadEvent) {
	Set("lblOut", "Caption", "ready")
	Call("lstLog", "AddItem", "Form1 loaded")
}

func cmdAdd_Click() {
	a := GetNum("txtA", "Text")
	b := GetNum("txtB", "Text")
	Set("lblOut", "Caption", a+b)
	// Helpers.go is in the same package: a plain Go call
	Call("lstLog", "AddItem", fmt.Sprintf("%v x %v = %v", a, b, multiply(a, b)))
}

func txtA_TextChanged() {
	Set("lblEcho", "Caption", Get("txtA", "Text"))
}

func chkBig_CheckedChanged() {
	if GetNum("chkBig", "Value") == 1 {
		Set("lblOut", "FontSize", 14)
		Set("lblOut", "Caption", "big")
	} else {
		Set("lblOut", "FontSize", 9)
		Set("lblOut", "Caption", "small")
	}
}

func optTwo_CheckedChanged() {
	Set("lblEcho", "Caption", Get("optTwo", "Value"))
}

func cboColor_SelectedIndexChanged() {
	Set("lblOut", "Caption", Get("cboColor", "Text"))
}

func tmrTick_Tick() {
	ticks++
	Set("lblTicks", "Caption", ticks)
	Set("prgTicks", "Value", ticks%51)
}

func cmdShow2_Click() { Show("Form2") }

func mnuForm2_Click() { Show("Form2") }

func mnuAbout_Click() { MsgBox("RAD IDE native Go demo") }

func mnuExit_Click() { End() }

func cmdMsg_Click() {
	MsgBox("Hello from radforms")
	Set("lblOut", "Caption", "msg done")
}

func cmdArabic_Click() {
	Set("lblOut", "Caption", "مرحبا بالعالم")
}
