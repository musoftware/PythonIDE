
function Form1_Load(e: RadEvent): void {
  const n: number = PyLib.Mul(3, 3);
  console.log('T1', n, PyLib.Hello('Tia'));
  console.log('T2', TsLib.Square(5));
}
