import MathF
print('ADD', MathF.add(2, 3.5))
print('GREET', MathF.greet('Ann'))
print('TWICE', MathF.twice(21))
print('POS', MathF.is_pos(4), MathF.is_pos(-1))
print('SHOW', MathF.show('x'))
print('LEGACY', MathF.legacy(6, 7))
print('HYP', MathF.hyp(3, 4))
from radcall import radcall
try:
    radcall('mathf.add', 1)
except Exception as e:
    print('ERR', e)
