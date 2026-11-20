package calc

func Add(a, b int) int { return a + b }

func Sign(n int) string {
	if n > 0 {
		return "positive"
	} else if n < 0 {
		return "negative"
	}
	return "zero"
}
