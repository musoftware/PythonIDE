// Module Strings: a plain script - its top-level functions are visible to every form.
function exclaim(text, mark) {
    return String(text) + (mark === undefined ? '!' : mark);
}
