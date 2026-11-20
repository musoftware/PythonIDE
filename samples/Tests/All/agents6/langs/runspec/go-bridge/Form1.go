package main

import "os"

func Form1_Load(e RadEvent) {
	Set("lblOut", "Caption", "hi")
	os.WriteFile("loaded.txt", []byte(Get("lblOut", "Caption")+"|"+Get("txtA", "Text")), 0644)
	End()
}

func cmdGo_Click() {}
