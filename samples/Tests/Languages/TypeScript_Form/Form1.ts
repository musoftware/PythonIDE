// Event handlers for Form1. A handler is a function named <Control>_<Event>(e: RadEvent).
// Controls: get("txtA", "Text"), set("lblOut", "Caption", x), call("lstLog", "AddItem", x)
//   or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.
// Other modules: radcall("Module.func", ...args). npm packages: const m = require("name").
// Types of the API: radgui.d.ts (copied into the project when it runs).

function Form1_Load(e: RadEvent): void {
    // runs when the form is shown
}

function cmdAdd_Click(e: RadEvent): void {
    const a: number = getNum("txtA", "Text");
    const b: number = getNum("txtB", "Text");
    const total: number = a + b;
    set("lblOut", "Caption", String(total));
}
