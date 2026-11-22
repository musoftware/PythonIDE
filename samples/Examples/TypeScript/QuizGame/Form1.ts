// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Quiz Game - a multiple-choice quiz in TypeScript with two RAD IDE forms.
// Shows: a Timer (10 seconds per question) driving a ProgressBar, four answer Buttons sharing one handler,
// changing captions and colors at run time, a second form (Results) shown with show("Results") and
// filled from this form, a best score kept in a JSON file, and English / Arabic question sets
// (Language menu) from the Questions.ts module.

const SECONDS = 10;

let lang: Lang = 'en';
let questions: Question[] = [];
let current = -1;
let score = 0;
let timeLeft = SECONDS;
let answers: string[] = [];

function Form1_Load(e: RadEvent): void {
    set('lblQuestion', 'Caption', ui_(lang).press);
}

// ------------------------------------------------------------------ game flow
function cmdStart_Click(e: RadEvent): void { newGame(); }
function mnuNew_Click(e: RadEvent): void { newGame(); }

function newGame(): void {
    questions = shuffled(questionSet(lang)).slice(0, 5);
    current = -1;
    score = 0;
    answers = [];
    hide('Results');
    set('cmdStart', 'Enabled', false);
    nextQuestion();
}

function nextQuestion(): void {
    current += 1;
    if (current >= questions.length) { finish(); return; }
    const q = questions[current];
    set('lblProgress', 'Caption', `${ui_(lang).question} ${current + 1} / ${questions.length}`);
    set('lblQuestion', 'Caption', q.text);
    ['cmdA', 'cmdB', 'cmdC', 'cmdD'].forEach((b, i) => {
        set(b, 'Caption', q.choices[i]);
        set(b, 'Enabled', true);
    });
    set('lblFeedback', 'Caption', '');
    timeLeft = SECONDS;
    set('prgTime', 'Value', SECONDS);
    set('tmrQuestion', 'Enabled', true);
}

function cmdA_Click(e: RadEvent): void { answer(0); }
function cmdB_Click(e: RadEvent): void { answer(1); }
function cmdC_Click(e: RadEvent): void { answer(2); }
function cmdD_Click(e: RadEvent): void { answer(3); }

function answer(choice: number): void {
    if (current < 0 || current >= questions.length) return;
    set('tmrQuestion', 'Enabled', false);
    const q = questions[current];
    const right = choice === q.answer;
    if (right) score += 1 + Math.floor(timeLeft / 4);          // faster answers earn a bonus
    answers.push(`${right ? '✔' : '✘'} ${q.text} -> ${q.choices[q.answer]}`);
    set('lblScore', 'Caption', `${ui_(lang).score}: ${score}`);
    set('lblFeedback', 'Caption', right ? ui_(lang).right : `${ui_(lang).wrong} ${q.choices[q.answer]}`);
    set('lblFeedback', 'ForeColor', right ? 0x008000 : 0x0000C0);     // VB colors are &HBBGGRR (green / red)
    nextQuestion();
}

function tmrQuestion_Tick(e: RadEvent): void {
    timeLeft -= 1;
    set('prgTime', 'Value', Math.max(0, timeLeft));
    if (timeLeft <= 0) answer(-1);                              // time is up = a wrong answer
}

function finish(): void {
    set('tmrQuestion', 'Enabled', false);
    set('cmdStart', 'Enabled', true);
    set('lblQuestion', 'Caption', `${ui_(lang).final}: ${score}`);
    const best = Math.max(score, readBest());
    writeBest(best);
    showResults(score, best, answers);                          // Results.ts
}

// ------------------------------------------------------------------ language menu
function mnuEnglish_Click(e: RadEvent): void { setLanguage('en'); }
function mnuArabic_Click(e: RadEvent): void { setLanguage('ar'); }
function mnuExit_Click(e: RadEvent): void { end(); }

function setLanguage(l: Lang): void {
    lang = l;
    set('cmdStart', 'Caption', ui_(l).start);
    set('lblQuestion', 'Caption', ui_(l).press);
    set('Form1', 'Caption', l === 'ar' ? 'لعبة الأسئلة - TypeScript' : 'Quiz Game - TypeScript');
}

// ------------------------------------------------------------------ best score file
function bestFile(): string { return require('path').join(__radfolder, 'quiz.best.json'); }

function readBest(): number {
    try { return Number(JSON.parse(require('fs').readFileSync(bestFile(), 'utf8')).best) || 0; } catch { return 0; }
}

function writeBest(best: number): void {
    require('fs').writeFileSync(bestFile(), JSON.stringify({ best }), 'utf8');
}

function shuffled<T>(list: T[]): T[] {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}
