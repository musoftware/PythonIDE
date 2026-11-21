// Event handlers for Form1. A handler is a function named <Control>_<Event>(e).
// Controls: get("txtA", "Text"), set("lblOut", "Caption", x), call("lstLog", "AddItem", x)
//   or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.
// Other modules: radcall("Module.func", ...args). npm packages: require("name").

function Form1_Load(e) {
    // runs when the form is shown
}

function rateFood_ValueChanged(e) {
    set("lblResult", "Caption", "Food " + get("rateFood", "Value") + "/" + get("rateFood", "MaxStars") + " - Service " + get("rateService", "Value") + "/" + get("rateService", "MaxStars"));

}

function rateService_ValueChanged(e) {
    set("lblResult", "Caption", "Food " + get("rateFood", "Value") + "/" + get("rateFood", "MaxStars") + " - Service " + get("rateService", "Value") + "/" + get("rateService", "MaxStars"));

}

function btnReset_Click(e) {
    call("rateFood", "Reset");
    call("rateService", "SetValue", 1);

}
