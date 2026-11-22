// RAD IDE - GUI Bridge client for Go (copied into the project when it runs).
//
// The IDE draws the forms; this program talks to it over stdin/stdout
// (protocol: docs/CONTRACTS.md section 1). Everything is synchronous.
// All project files are in package main.
//
//	Set(obj, prop, value)               set a property     Set("lblOut", "Caption", "Hi")
//	Get(obj, prop) string               read a property    Get("txtA", "Text")
//	GetNum(obj, prop) float64           read a property as a number
//	Call(obj, method, args...) string   call a method      Call("lstLog", "AddItem", "line")
//	MsgBox(text)                        message box (waits for OK)
//	Input(prompt) string                input box
//	Show(form) / Hide(form)             show or hide a form
//	End()                               quit the program
//	radcall("Module.func", args...) any            call a function of any project module, in
//	radcallE("Module.func", args...) (any, error)  any language, through the RAD Hub (JSON values;
//	                                               numbers arrive as float64). radcall panics on error.
//
// Handlers are functions named <Control>_<Event> with no parameters or one RadEvent
// (e.X, e.Y, e.Button, e.KeyCode, e.KeyChar, e.Args).
package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
)

// RadEvent holds the event arguments (mouse/key events; zeros otherwise).
type RadEvent struct {
	Object, Event, Args string
	X, Y, Button, KeyCode int
	KeyChar               string
}

var (
	radIn     = bufio.NewReaderSize(os.Stdin, 65536)
	radOut    io.Writer = os.Stdout
	radWorker bool // true inside a RAD Hub worker: no IDE on stdin/stdout
	radMu     sync.Mutex
)

func radClean(v any) string {
	s := fmt.Sprint(v)
	s = strings.ReplaceAll(s, "\r\n", " ")
	return strings.ReplaceAll(s, "\n", " ")
}

// radEsc: a value for an "ESC" command (\\ newline CR escaped: multi-line text survives the line protocol)
func radEsc(v any) string {
	s := strings.ReplaceAll(fmt.Sprint(v), `\`, `\\`)
	s = strings.ReplaceAll(s, "\n", `\n`)
	return strings.ReplaceAll(s, "\r", `\r`)
}

// radUnesc: the answer to an "ESC" command, unescaped
func radUnesc(s string) string {
	if !strings.Contains(s, `\`) {
		return s
	}
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' && i+1 < len(s) && strings.IndexByte(`\nr`, s[i+1]) >= 0 {
			i++
			switch s[i] {
			case 'n':
				b.WriteByte('\n')
			case 'r':
				b.WriteByte('\r')
			default:
				b.WriteByte('\\')
			}
			continue
		}
		b.WriteByte(s[i])
	}
	return b.String()
}

func radSend(line string) {
	if radWorker {
		fmt.Fprintln(os.Stderr, line)
		return
	}
	io.WriteString(radOut, line+"\n")
}

func radReadLine() string {
	if radWorker {
		return ""
	}
	line, err := radIn.ReadString('\n')
	if err != nil && line == "" {
		os.Exit(0) // the IDE went away
	}
	return strings.TrimRight(line, "\r\n")
}

// Set sets a property: Set("lblOut", "Caption", "Hi").
func Set(obj, prop string, value any) {
	radMu.Lock()
	defer radMu.Unlock()
	radSend("ESC SET " + obj + " " + prop + " " + radEsc(value))
}

// Get reads a property as text: Get("txtA", "Text").
func Get(obj, prop string) string {
	radMu.Lock()
	defer radMu.Unlock()
	radSend("ESC GET " + obj + " " + prop)
	return radUnesc(radReadLine())
}

// GetNum reads a property as a number (0 when it is not numeric).
func GetNum(obj, prop string) float64 {
	s := strings.TrimSpace(Get(obj, prop))
	end := 0
	for end < len(s) && strings.ContainsRune("+-0123456789.eE", rune(s[end])) {
		end++
	}
	for end > 0 {
		if f, err := strconv.ParseFloat(s[:end], 64); err == nil {
			return f
		}
		end--
	}
	return 0
}

// Call calls a method: Call("lstLog", "AddItem", "text"). Returns the answer as text.
func Call(obj, method string, args ...any) string {
	radMu.Lock()
	defer radMu.Unlock()
	line := "ESC CALL " + obj + " " + method
	if len(args) > 0 {
		parts := make([]string, len(args))
		for i, a := range args {
			parts[i] = radEsc(a)
		}
		line += " " + strings.Join(parts, "\t")
	}
	radSend(line)
	return radUnesc(radReadLine())
}

// MsgBox shows a message box and waits for OK.
func MsgBox(text any) string {
	radMu.Lock()
	defer radMu.Unlock()
	radSend("ESC MSGBOX " + radEsc(text))
	return radUnesc(radReadLine())
}

// Input shows an input box and returns the text.
func Input(prompt any) string {
	radMu.Lock()
	defer radMu.Unlock()
	radSend("ESC INPUT " + radEsc(prompt))
	return radUnesc(radReadLine())
}

// Show shows a form.
func Show(form string) { radSend("SHOW " + form) }

// Hide hides a form.
func Hide(form string) { radSend("HIDE " + form) }

// End quits the program.
func End() {
	radSend("END")
	os.Exit(0)
}

// ------------------------------------------------------------------ RAD Hub
var (
	radHub     net.Conn
	radHubIn   *bufio.Reader
	radHubID   int
	radHubLock sync.Mutex
)

// radcallE calls a function of any project module through the RAD Hub.
func radcallE(name string, args ...any) (any, error) {
	radHubLock.Lock()
	defer radHubLock.Unlock()
	addr := os.Getenv("RAD_HUB")
	if addr == "" {
		return nil, fmt.Errorf("radcall(%s): RAD Hub is not running (RAD_HUB is not set)", name)
	}
	if radHub == nil {
		c, err := net.Dial("tcp", addr)
		if err != nil {
			return nil, fmt.Errorf("radcall(%s): cannot connect to RAD Hub at %s: %v", name, addr, err)
		}
		radHub, radHubIn = c, bufio.NewReaderSize(c, 65536)
	}
	if args == nil {
		args = []any{}
	}
	radHubID++
	id := radHubID
	req, err := json.Marshal(map[string]any{"id": id, "call": name, "args": args})
	if err != nil {
		return nil, fmt.Errorf("radcall(%s): %v", name, err)
	}
	if _, err := radHub.Write(append(req, '\n')); err != nil {
		radHub.Close()
		radHub = nil
		return nil, fmt.Errorf("radcall(%s): %v", name, err)
	}
	for {
		line, err := radHubIn.ReadString('\n')
		if err != nil && line == "" {
			radHub.Close()
			radHub = nil
			return nil, fmt.Errorf("radcall(%s): RAD Hub closed the connection", name)
		}
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var msg struct {
			ID     *float64        `json:"id"`
			Result any             `json:"result"`
			Error  json.RawMessage `json:"error"`
		}
		if json.Unmarshal([]byte(line), &msg) != nil || msg.ID == nil || int(*msg.ID) != id {
			continue
		}
		if len(msg.Error) > 0 && string(msg.Error) != "null" {
			var text string
			if json.Unmarshal(msg.Error, &text) != nil {
				text = string(msg.Error)
			}
			return nil, errors.New("radcall(" + name + "): " + text)
		}
		return msg.Result, nil
	}
}

// radcall is radcallE that panics on error (the event handler reports it).
func radcall(name string, args ...any) any {
	r, err := radcallE(name, args...)
	if err != nil {
		panic(err)
	}
	return r
}

// ------------------------------------------------------------------ main loop
func radParseEvent(obj, ev, rest string) RadEvent {
	e := RadEvent{Object: obj, Event: ev, Args: rest}
	p := strings.SplitN(rest, " ", 5)
	num := func(i int) int {
		if i >= len(p) {
			return 0
		}
		f, _ := strconv.ParseFloat(p[i], 64)
		return int(f)
	}
	e.X, e.Y, e.Button, e.KeyCode = num(0), num(1), num(2), num(3)
	if len(p) > 4 {
		e.KeyChar = p[4]
	}
	return e
}

func radRunHandler(name string, h func(RadEvent), e RadEvent) {
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "[Go] error in %s: %v\n", name, r)
		}
	}()
	h(e)
}

// radRun reads EVENT lines and runs the matching handler; it always answers DONE.
func radRun(handlers map[string]func(RadEvent)) {
	lower := map[string]func(RadEvent){}
	for k, v := range handlers {
		lower[strings.ToLower(k)] = v
	}
	// started without RAD IDE (double-clicked): nobody on stdin draws the forms - say so
	if st, err := os.Stdin.Stat(); err == nil && st.Mode()&os.ModeCharDevice != 0 && os.Getenv("RAD_HANDLERS") == "" {
		fmt.Println("This program is a RAD IDE GUI Bridge client: its forms are drawn by RAD IDE.")
		fmt.Println("Run it from the IDE (F5), or make a standalone exe with the forms inside:")
		fmt.Println("Build > Build Native Exe (or Build > Publish).")
		fmt.Println()
		fmt.Println("Press Enter to close.")
		radIn.ReadString('\n')
		os.Exit(0)
	}
	failed := 0
	for {
		line, err := radIn.ReadString('\n')
		if err != nil && line == "" {
			// under the IDE debugger (RAD_BRIDGE_DEBUG) Delve halts the process to change breakpoints, which
			// aborts the pending read of stdin on Windows: read again (only the end of stdin ends the program)
			if err != io.EOF && os.Getenv("RAD_BRIDGE_DEBUG") != "" && failed < 1000 {
				failed++
				continue
			}
			break
		}
		line = strings.TrimRight(line, "\r\n")
		if line == "QUIT" {
			break
		}
		if !strings.HasPrefix(line, "EVENT ") {
			continue
		}
		parts := strings.SplitN(line[6:], " ", 3)
		if len(parts) >= 2 {
			name := parts[0] + "_" + parts[1]
			h, ok := handlers[name]
			if !ok {
				h, ok = lower[strings.ToLower(name)]
			}
			if ok {
				rest := ""
				if len(parts) > 2 {
					rest = parts[2]
				}
				radRunHandler(name, h, radParseEvent(parts[0], parts[1], rest))
			}
		}
		io.WriteString(radOut, "DONE\n")
	}
	if radHub != nil {
		radHub.Close()
	}
	os.Exit(0)
}

// keep the helpers referenced so `go vet` does not report them as unused in small projects
var _ = []any{Set, Get, GetNum, Call, MsgBox, Input, Show, Hide, End, radcall, radcallE, radRun}
