// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Handlers of the Results form. Form1 calls showResults() when a game ends; the form is shown with
// show("Results") and hidden again by its own buttons.

function Results_Load(e: RadEvent): void {
}

/** Fill the Results form and show it. */
function showResults(score: number, best: number, lines: string[]): void {
    set('Results.lblTitle', 'Caption', `Score: ${score}`);
    call('Results.lstAnswers', 'Clear');
    for (const l of lines) call('Results.lstAnswers', 'AddItem', l);
    set('Results.lblBest', 'Caption', score >= best ? 'New best score!' : `Best score: ${best}`);
    show('Results');
}

function cmdAgain_Click(e: RadEvent): void {
    hide('Results');
    newGame();
}

function cmdClose_Click(e: RadEvent): void {
    hide('Results');
}
