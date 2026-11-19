import MathC, TextCpp
print('ADD', MathC.Add(2, 3.5))
print('GREET', MathC.Greet('Ann'))
print('TWICE', MathC.Twice(21))
print('EVEN', MathC.IsEven(4), MathC.IsEven(5))
print('LOG', MathC.Log('x'))
print('SUM3', MathC.Sum3(1, 2, 3))
print('JOIN', TextCpp.Join('a', 'b'))
print('SQ', TextCpp.Square(1.5))
print('CPLUS', TextCpp.CPlus(4, 5))
from radcall import radcall
try:
    radcall('mathc.Add', 1)
except Exception as e:
    print('ERR', e)
