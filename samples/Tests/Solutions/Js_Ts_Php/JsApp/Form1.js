
function Form1_Load(e) {
  console.log('J1', PyLib.Mul(6, 7));
  const P = require('./PyLib.ref');
  console.log('J2', P.Hello('Bob'));
  console.log('J3', JsLib.Add(1, 2), JsLib.Add(5));
  console.log('J4', PhpLib.Shout('hey'));
  console.log('J5', JSON.stringify(JsLib.Stats([4, 5])));
  try { PyLib.Mul(); } catch (err) { console.log('J6 error ok', /Mul/.test(String(err.message))); }
}
