// Event handlers for Form1. A handler is a function named <Control>_<Event>(e).
// Controls: get("txtA", "Text"), set("lblOut", "Caption", x), call("lstLog", "AddItem", x)
//   or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.
// Other modules: radcall("Module.func", ...args). npm packages: require("name").

function Form1_Load(e) {
    log("Form loaded - Node.js " + process.version);
}

function cmdHello_Click(e) {
    const name = ui.txtName.Text.trim() || "World";
    ui.lblResult.Caption = greeting(name);          // greeting() lives in Helpers.js
    log("Hello " + name);
}

function cmdAdd_Click(e) {
    const a = getNum("txtA", "Text");
    const b = getNum("txtB", "Text");
    set("lblResult", "Caption", `${a} + ${b} = ${add(a, b)}`);
    log(`add(${a}, ${b})`);
}

function txtName_KeyPress(e) {
    if (e.KeyCode === 13) cmdHello_Click(e);       // Enter
}

function mnuFileClear_Click(e) {
    ui.lstLog.Clear();
    ui.lblResult.Caption = "";
}

function mnuFileExit_Click(e) {
    end();
}

function mnuHelpAbout_Click(e) {
    msgbox("Hello JavaScript - a RAD IDE sample running on Node.js through the GUI Bridge.");
}

function log(text) {
    const t = new Date().toLocaleTimeString();
    call("lstLog", "AddItem", `${t}  ${text}`);
}
