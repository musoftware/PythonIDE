# Event handlers for Form1. A handler is a function named <Control>_<Event>;
# $e has X, Y, Button, KeyCode, KeyChar. Use $script:name for variables kept between events.
# Controls are objects made in Form1_designer.ps1:  $lblOut.Text = "Hi";  $lstLog.AddItem("x")
# Helpers: MsgBox "text", InputBox "prompt", RadSet/RadGet/RadInvoke obj ..., RadShow Form2, RadEnd,
#          radcall "Module.function" arg1 arg2 - call a function of a project module.

function Form1_Load($e) {
    # runs when the form is shown
}
