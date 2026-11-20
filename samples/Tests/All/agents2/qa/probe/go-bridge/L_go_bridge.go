// Class library L_go_bridge (package main). Its exported (Capitalized) functions are public:
// projects that reference L_go_bridge call them as code of their own language
// (Python: L_go_bridge.Add(2, 3), Go: L_go_bridge.Add(2, 3), ...). A last error result becomes an error.
package main

// Add adds two numbers. Exported (Capitalized) functions can be called by every project
// that references this one (arguments/results are converted with encoding/json).
func Add(a, b float64) float64 {
	return a + b
}
