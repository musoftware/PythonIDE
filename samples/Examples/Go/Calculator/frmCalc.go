// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in Go (RAD IDE GUI Bridge; Build > Publish makes an exe).
//
// The arithmetic is a small engine type (calcEngine) whose methods return errors (Go style) instead of
// throwing; the handlers turn buttons and keys into engine calls and show the result or the error.
// Shows: many buttons, keyboard input on the form (KeyPress: the key name is in e.Args), error values,
// strconv number formatting, a memory register.
package main

import (
	"errors"
	"math"
	"strconv"
	"strings"
)

type calcEngine struct {
	display, expression string
	acc, memory         float64
	op                  byte
	fresh, failed       bool
}

var calc = &calcEngine{display: "0", fresh: true}

var errDivZero = errors.New("division by zero")

func format(x float64) string { return strconv.FormatFloat(x, 'g', 15, 64) }

func (c *calcEngine) value() float64 {
	v, _ := strconv.ParseFloat(c.display, 64)
	return v
}

func (c *calcEngine) show(x float64) error {
	if math.IsNaN(x) || math.IsInf(x, 0) || math.Abs(x) > 1e15 {
		return errors.New("overflow")
	}
	c.display = format(x)
	return nil
}

func (c *calcEngine) digit(d string) error {
	if c.failed {
		c.clear()
	}
	if c.fresh {
		c.display, c.fresh = "", false
		if d == "." {
			c.display = "0"
		}
	}
	if (d == "." && strings.Contains(c.display, ".")) || len(c.display) >= 16 {
		return nil
	}
	if c.display == "0" && d != "." {
		c.display = ""
	}
	c.display += d
	return nil
}

func (c *calcEngine) apply() error {
	x := c.value()
	switch c.op {
	case '+':
		c.acc += x
	case '-':
		c.acc -= x
	case '*':
		c.acc *= x
	case '/':
		if x == 0 {
			return errDivZero
		}
		c.acc /= x
	default:
		c.acc = x
	}
	return c.show(c.acc)
}

func (c *calcEngine) operation(o byte) error {
	if c.failed {
		return nil
	}
	if !c.fresh || c.op == 0 {
		if err := c.apply(); err != nil {
			return err
		}
	}
	c.op, c.fresh = o, true
	c.expression = format(c.acc) + " " + string(o)
	return nil
}

func (c *calcEngine) result() error {
	if c.failed || c.op == 0 {
		return nil
	}
	if err := c.apply(); err != nil {
		return err
	}
	c.op, c.fresh, c.expression = 0, true, ""
	return nil
}

func (c *calcEngine) clear() error {
	*c = calcEngine{display: "0", fresh: true, memory: c.memory}
	return nil
}

func (c *calcEngine) unary(what byte) error {
	if c.failed {
		return nil
	}
	x := c.value()
	switch what {
	case 'n':
		x = -x
	case 's':
		if x < 0 {
			return errors.New("negative square root")
		}
		x = math.Sqrt(x)
		c.fresh = true
	case '%':
		if c.op != 0 {
			x = c.acc * x / 100
		} else {
			x /= 100
		}
	}
	return c.show(x)
}

func (c *calcEngine) back() error {
	if c.failed || c.fresh {
		return nil
	}
	c.display = c.display[:len(c.display)-1]
	if c.display == "" || c.display == "-" {
		c.display = "0"
	}
	return nil
}

// run one engine call, show the result or the error
func do(f func() error) {
	if err := f(); err != nil {
		calc.display, calc.expression, calc.failed, calc.op, calc.fresh = "Error: "+err.Error(), "", true, 0, true
	}
	Set("lblDisplay", "Caption", calc.display)
	Set("lblExpr", "Caption", calc.expression)
	m := ""
	if calc.memory != 0 {
		m = "M"
	}
	Set("lblMemory", "Caption", m)
}

func digitFn(d string) func() error { return func() error { return calc.digit(d) } }
func opFn(o byte) func() error      { return func() error { return calc.operation(o) } }
func unaryFn(w byte) func() error   { return func() error { return calc.unary(w) } }

func frmCalc_Load()     { do(func() error { return nil }) }
func btn0_Click()       { do(digitFn("0")) }
func btn1_Click()       { do(digitFn("1")) }
func btn2_Click()       { do(digitFn("2")) }
func btn3_Click()       { do(digitFn("3")) }
func btn4_Click()       { do(digitFn("4")) }
func btn5_Click()       { do(digitFn("5")) }
func btn6_Click()       { do(digitFn("6")) }
func btn7_Click()       { do(digitFn("7")) }
func btn8_Click()       { do(digitFn("8")) }
func btn9_Click()       { do(digitFn("9")) }
func btnDot_Click()     { do(digitFn(".")) }
func btnAdd_Click()     { do(opFn('+')) }
func btnSub_Click()     { do(opFn('-')) }
func btnMul_Click()     { do(opFn('*')) }
func btnDiv_Click()     { do(opFn('/')) }
func btnEquals_Click()  { do(calc.result) }
func btnClear_Click()   { do(calc.clear) }
func btnSign_Click()    { do(unaryFn('n')) }
func btnSqrt_Click()    { do(unaryFn('s')) }
func btnPercent_Click() { do(unaryFn('%')) }
func btnBack_Click()    { do(calc.back) }
func btnMC_Click()      { do(func() error { calc.memory = 0; return nil }) }

func btnMR_Click() {
	do(func() error {
		calc.fresh = true
		return calc.show(calc.memory)
	})
}

func btnMPlus_Click() {
	do(func() error {
		calc.memory += calc.value()
		calc.fresh = true
		return nil
	})
}

// the form gets the keys of all its controls; e.Args = "X Y Button KeyName KeyChar"
func frmCalc_KeyPress(e RadEvent) {
	parts := strings.Fields(e.Args)
	key := ""
	if len(parts) > 3 {
		key = parts[3]
	}
	ch := e.KeyChar
	switch {
	case len(ch) == 1 && ch[0] >= '0' && ch[0] <= '9':
		do(digitFn(ch))
	case ch == "." || ch == ",":
		do(digitFn("."))
	case len(ch) == 1 && strings.Contains("+-*/", ch):
		do(opFn(ch[0]))
	case ch == "=" || key == "Return" || key == "13":
		do(calc.result)
	case key == "Escape" || key == "27":
		do(calc.clear)
	case key == "BackSpace" || key == "8":
		do(calc.back)
	}
}
