// Module Helpers. Its top-level functions can be called
//   - directly from the JavaScript forms of this project: add(2, 3)
//   - from any other language through RAD Hub: radcall("Helpers.add", 2, 3)
// Arguments and results are JSON values (number, string, bool, null, array, object).

function add(a, b) {
    return a + b;
}

function greeting(name) {
    const hour = new Date().getHours();
    const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
    return `Good ${part}, ${name}!`;
}
