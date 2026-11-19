import MathRs
print('ADD', MathRs.add(2, 3.5))
print('GREET', MathRs.greet('Ann'))
print('TWICE', MathRs.twice(21))
print('EVEN', MathRs.is_even(4), MathRs.is_even(5))
print('TOTAL', MathRs.total([1, 2, 3.5]))
print('WORDS', MathRs.words('a b c'))
print('DIV', MathRs.safe_div(1, 4))
try:
    MathRs.safe_div(1, 0)
except Exception as e:
    print('ERR', e)
print('LOG', MathRs.log('x'))
from radcall import radcall
print('LEGACY', radcall('mathrs.legacy', 1, 2, 3))
