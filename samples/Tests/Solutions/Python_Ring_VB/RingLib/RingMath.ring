# Multiply
func Mul a, b
	return a * b

func Shout s
	return upper(s) + "!"

func Items n
	aList = []
	for i = 1 to n add(aList, i * 10) next
	return aList
