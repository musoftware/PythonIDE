package main

import "fmt"

func Form1_Load(e RadEvent) {
	Set("lblOut", "Caption", "loaded")
}

func cmdGo_Click(e RadEvent) {
	t := Get("txtA", "Text")
	n := radcall("Helpers.add", 2, 3)
	m := radcall("Helpers.add", n, 2)
	Set("lblOut", "Caption", fmt.Sprintf("%s|%v|%v", t, n, m))
	Call("lstLog", "AddItem", t)
}

func cmdBoom_Click() {
	panic("boom on purpose")
}

func cmdErr_Click(e RadEvent) {
	if _, err := radcallE("Helpers.nope"); err != nil {
		Set("lblErr", "Caption", "err "+err.Error())
	} else {
		Set("lblErr", "Caption", "noerror")
	}
}
