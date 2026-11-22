// Event handlers for Form2.
package main

func Form2_Load() {
	Set("txt2", "Text", "from Form2 Load")
}

func cmdClose2_Click() {
	Set("Form1.lblOut", "Caption", Get("txt2", "Text"))
	Hide("Form2")
}
