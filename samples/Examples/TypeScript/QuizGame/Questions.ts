// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module Questions - the question sets and interface texts of the Quiz Game (English and Arabic).

type Lang = 'en' | 'ar';

interface Question {
    text: string;
    choices: [string, string, string, string];
    answer: number;              // index of the right choice
}

const QUESTIONS: Record<Lang, Question[]> = {
    en: [
        { text: 'Which planet is the largest?', choices: ['Mars', 'Jupiter', 'Venus', 'Earth'], answer: 1 },
        { text: 'How many bits are in a byte?', choices: ['4', '16', '8', '10'], answer: 2 },
        { text: 'What is 7 x 8?', choices: ['56', '54', '64', '48'], answer: 0 },
        { text: 'Which language runs in every web browser?', choices: ['Python', 'C', 'Ruby', 'JavaScript'], answer: 3 },
        { text: 'The longest river in Africa is the...', choices: ['Congo', 'Nile', 'Niger', 'Zambezi'], answer: 1 },
        { text: 'H2O is the formula of...', choices: ['Salt', 'Oxygen', 'Water', 'Hydrogen'], answer: 2 },
        { text: 'How many sides has a hexagon?', choices: ['6', '5', '8', '7'], answer: 0 },
    ],
    ar: [
        { text: 'ما هو أكبر كوكب في المجموعة الشمسية؟', choices: ['المريخ', 'المشتري', 'الزهرة', 'الأرض'], answer: 1 },
        { text: 'كم عدد البتات في البايت؟', choices: ['4', '16', '8', '10'], answer: 2 },
        { text: 'كم يساوي 7 × 8؟', choices: ['56', '54', '64', '48'], answer: 0 },
        { text: 'ما هي عاصمة مصر؟', choices: ['الإسكندرية', 'أسوان', 'الأقصر', 'القاهرة'], answer: 3 },
        { text: 'أطول نهر في أفريقيا هو...', choices: ['الكونغو', 'النيل', 'النيجر', 'زامبيزي'], answer: 1 },
        { text: 'الصيغة H2O هي صيغة...', choices: ['الملح', 'الأكسجين', 'الماء', 'الهيدروجين'], answer: 2 },
        { text: 'كم عدد أضلاع الشكل السداسي؟', choices: ['6', '5', '8', '7'], answer: 0 },
    ],
};

const TEXTS = {
    en: { press: 'Press Start to play', question: 'Question', score: 'Score', right: 'Right!',
          wrong: 'Wrong - the answer is', final: 'Game over - your score', start: 'Start' },
    ar: { press: 'اضغط ابدأ للعب', question: 'السؤال', score: 'النقاط', right: 'إجابة صحيحة!',
          wrong: 'خطأ - الإجابة الصحيحة', final: 'انتهت اللعبة - نقاطك', start: 'ابدأ' },
};

function questionSet(lang: Lang): Question[] { return QUESTIONS[lang]; }

function ui_(lang: Lang) { return TEXTS[lang]; }
