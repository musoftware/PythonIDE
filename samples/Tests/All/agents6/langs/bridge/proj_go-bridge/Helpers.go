package main

import (
	"errors"
	"fmt"
)

func add(a, b int) int {
	fmt.Println("logged add")
	return a + b
}

func greet(who string) string { return "Hello, " + who }

func info() map[string]any { return map[string]any{"a": []int{1, 2}, "s": "x"} }

func fail() (int, error) { return 0, errors.New("bad thing") }
