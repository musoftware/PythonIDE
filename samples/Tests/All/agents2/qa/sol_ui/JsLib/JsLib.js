// Class Library module JsLib. Every top-level function here is public: a project that
// references this library calls it as native code, e.g. JsLib.Add(2, 3) in JavaScript,
// JsLib.Add(2, 3) in Python/C#, JsLib::Add(2, 3) in PHP. Names starting with _ stay private.
// Arguments and results are JSON values (number, string, bool, null, array, object).

/** Add two numbers and return the sum. */
function Add(a, b) {
    return a + b;
}

/** Say hello to someone. */
function Greet(name) {
    return `Hello, ${name}!`;
}
