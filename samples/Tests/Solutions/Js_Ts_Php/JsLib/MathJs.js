
/** Add two numbers. */
function add(a, b = 10) { return a + b; }
function _private() { return 0; }
module.exports = {
  Add: add,
  Greet(name) { return 'Hello ' + name + ' from JS, ' + PhpLib.Shout(name); },  // JsLib -> PhpLib (reference)
  Stats: (xs) => ({ n: xs.length, sum: xs.reduce((s, x) => s + x, 0) }),
};
