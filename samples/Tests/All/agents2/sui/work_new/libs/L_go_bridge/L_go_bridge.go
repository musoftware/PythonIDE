// Module L_go_bridge (package main: its functions can be called directly from Go code).
// Other languages call its functions through the RAD Hub: radcall("L_go_bridge.hello", "x")
// (arguments and the result are JSON values; a last error result becomes an error).
// From Go: r := radcall("Other.func", 1, 2)  or  r, err := radcallE(...)
package main

func hello(who string) string {
	return "Hello, " + who
}
// Public functions of L_go_bridge go here - projects that reference L_go_bridge can call them.
