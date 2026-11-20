// Class Library module TsLib. Every top-level function here is public: a project that
// references this library calls it as native code, e.g. TsLib.Add(2, 3) in JavaScript,
// TsLib.Add(2, 3) in Python/C#, TsLib::Add(2, 3) in PHP. Names starting with _ stay private.
// Arguments and results are JSON values (number, string, bool, null, array, object).

/** Add two numbers and return the sum. */
function Add(a: number, b: number): number {
    return a + b;
}

/** Say hello to someone. */
function Greet(name: string): string {
    return `Hello, ${name}!`;
}
