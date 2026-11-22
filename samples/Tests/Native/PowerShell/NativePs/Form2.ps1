function Form2_Load($e) {
    $lblMsg.Text = "Form2 loaded"
}

function btnBack_Click($e) {
    RadSet "Form1.lblOut" "Text" "From Form2"
    RadHide Form2
}
