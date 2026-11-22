// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module TextUtils - plain functions used by Form1.js (and callable from other languages of a solution
// through RAD Hub: radcall("TextUtils.textStats", "some text")).

/** Lines, words and characters of a text (Arabic and other scripts count as words too). */
function textStats(text) {
    const t = String(text || '').replace(/\r\n/g, '\n');      // the TextBox answers with CR LF line ends
    const words = t.trim() ? t.trim().split(/\s+/u).length : 0;
    const lines = t ? t.split(/\r\n|\r|\n/).length : 0;
    return { lines, words, chars: [...t].length };
}

/** How many times `what` occurs in `text` (case sensitive, not overlapping). */
function countOccurrences(text, what) {
    if (!what) return 0;
    return String(text).split(what).length - 1;
}

/** The lines sorted alphabetically (locale aware, so Arabic sorts correctly). */
function sortLines(text) {
    const lines = String(text).split(/\r\n|\r|\n/);
    return lines.sort((a, b) => a.localeCompare(b)).join('\n');
}
