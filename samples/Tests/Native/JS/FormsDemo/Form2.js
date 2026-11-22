// Event handlers for Form2. exclaim() comes from Strings.js (the project's files share one global scope).
function Form2_Load(e) {
    set('txt2', 'Text', 'from Form2 Load');
}

function cmdClose2_Click(e) {
    set('Form1.lblOut', 'Caption', exclaim(get('txt2', 'Text'), ''));
    hide('Form2');
}
