// Debugger test (Go / Delve): breakpoints, steps, expandable Locals, hit counts, logpoints.
package main

import "fmt"

type Point struct {
	X, Y  int
	Label string
}

func square(n int) int {
	result := n * n
	return result
}

func Form1_Load(e RadEvent) {
	numbers := []int{3, 1, 4, 1, 5}
	p := Point{X: 10, Y: 20, Label: "corner"}
	name := "RAD"
	total := 0
	for i := 0; i < len(numbers); i++ {
		total += square(numbers[i])
	}
	fmt.Println("total=", total, name, p.Label)
}
