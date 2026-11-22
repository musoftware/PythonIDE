// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a text editor in Go (RAD IDE GUI Bridge: the IDE draws frmMain, these functions handle its events;
// Build > Publish makes an exe).
//
// Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, os.ReadFile / os.WriteFile, the Windows clipboard
// (user32 through the syscall package - no cgo), Find / Find Next / Replace with SelStart / SelLength / SelText,
// a status bar, "discard changes?" questions, errors as values.
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unicode/utf8"
	"unsafe"
)

const maxText = 60000 // a GUI Bridge answer is one line of at most 64 KB

var (
	fileName, findWhat string
	dirty, loading     bool
)

// ------------------------------------------------------------------ helpers
func updateTitle() {
	name := "Untitled"
	if fileName != "" {
		name = filepath.Base(fileName)
	}
	star := ""
	if dirty {
		star = "*"
	}
	Set("frmMain", "Caption", star+name+" - Notepad")
}

func status(s string) { Set("sbStatus", "Text", s) }

func setDoc(text string) {
	loading = true
	Set("txtDoc", "Text", text)
	loading = false
}

func confirmDiscard() bool {
	if !dirty {
		return true
	}
	a := Input("The text has changed. Type YES to discard the changes (or Cancel to keep them):")
	return strings.HasPrefix(strings.ToLower(a), "y")
}

func writeFile(path string) bool {
	text := Get("txtDoc", "Text")
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		MsgBox("Cannot write " + path + ":\n" + err.Error())
		return false
	}
	fileName, dirty = path, false
	updateTitle()
	status(fmt.Sprintf("Saved %s (%d bytes)", filepath.Base(path), len(text)))
	return true
}

func openFile(path string) {
	data, err := os.ReadFile(path)
	if err != nil {
		MsgBox("Cannot open " + path + ":\n" + err.Error())
		return
	}
	cut := len(data) > maxText
	if cut {
		data = data[:maxText]
	}
	text := strings.TrimPrefix(string(data), string([]byte{0xEF, 0xBB, 0xBF}))      // UTF-8 BOM
	text = strings.ReplaceAll(strings.ReplaceAll(text, "\r\n", "\n"), "\n", "\r\n") // an edit box needs CR LF
	setDoc(text)
	fileName, dirty = path, false
	updateTitle()
	msg := "Opened " + filepath.Base(path)
	if cut {
		msg += " (only the first 60000 bytes)"
	}
	status(msg)
}

// SelStart / SelLength count characters; Go strings are UTF-8 bytes
func charIndex(s string, byteOff int) int { return utf8.RuneCountInString(s[:byteOff]) }

func byteIndex(s string, chars int) int {
	i := 0
	for n := 0; i < len(s) && n < chars; n++ {
		_, size := utf8.DecodeRuneInString(s[i:])
		i += size
	}
	return i
}

func findNext() bool {
	if findWhat == "" {
		return false
	}
	text := Get("txtDoc", "Text")
	from := byteIndex(text, int(GetNum("txtDoc", "SelStart")+GetNum("txtDoc", "SelLength")))
	lower, what := strings.ToLower(text), strings.ToLower(findWhat)
	hit := strings.Index(lower[from:], what)
	if hit >= 0 {
		hit += from
	} else {
		hit = strings.Index(lower, what) // wrap around
	}
	if hit < 0 {
		status(fmt.Sprintf("Cannot find %q", findWhat))
		return false
	}
	Set("txtDoc", "SelStart", charIndex(text, hit))
	Set("txtDoc", "SelLength", utf8.RuneCountInString(findWhat))
	Call("txtDoc", "SetFocus")
	status(fmt.Sprintf("Found %q at character %d", findWhat, charIndex(text, hit)+1))
	return true
}

// ------------------------------------------------------------------ clipboard (Win32)
var (
	user32           = syscall.NewLazyDLL("user32.dll")
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	openClipboard    = user32.NewProc("OpenClipboard")
	closeClipboard   = user32.NewProc("CloseClipboard")
	emptyClipboard   = user32.NewProc("EmptyClipboard")
	getClipboardData = user32.NewProc("GetClipboardData")
	setClipboardData = user32.NewProc("SetClipboardData")
	globalAlloc      = kernel32.NewProc("GlobalAlloc")
	globalLock       = kernel32.NewProc("GlobalLock")
	globalUnlock     = kernel32.NewProc("GlobalUnlock")
)

const cfUnicodeText, gmemMoveable = 13, 2

func clipboardPut(s string) {
	u, err := syscall.UTF16FromString(s)
	if err != nil {
		return
	}
	if r, _, _ := openClipboard.Call(0); r == 0 {
		return
	}
	defer closeClipboard.Call()
	emptyClipboard.Call()
	mem, _, _ := globalAlloc.Call(gmemMoveable, uintptr(len(u)*2))
	if mem == 0 {
		return
	}
	p, _, _ := globalLock.Call(mem)
	copy(unsafe.Slice((*uint16)(unsafe.Pointer(p)), len(u)), u)
	globalUnlock.Call(mem)
	setClipboardData.Call(cfUnicodeText, mem)
}

func clipboardGet() string {
	if r, _, _ := openClipboard.Call(0); r == 0 {
		return ""
	}
	defer closeClipboard.Call()
	h, _, _ := getClipboardData.Call(cfUnicodeText)
	if h == 0 {
		return ""
	}
	p, _, _ := globalLock.Call(h)
	defer globalUnlock.Call(h)
	var u []uint16
	for ptr := (*uint16)(unsafe.Pointer(p)); *ptr != 0; ptr = (*uint16)(unsafe.Add(unsafe.Pointer(ptr), 2)) {
		u = append(u, *ptr)
	}
	return syscall.UTF16ToString(u)
}

// ------------------------------------------------------------------ events
func frmMain_Load() {
	updateTitle()
	status("Ready - File > Open to load a text file")
}

func txtDoc_TextChanged() {
	if loading || dirty {
		return
	}
	dirty = true
	updateTitle()
}

func mnuNew_Click() {
	if !confirmDiscard() {
		return
	}
	setDoc("")
	fileName, dirty = "", false
	updateTitle()
	status("New document")
}

func mnuOpen_Click() {
	if !confirmDiscard() || Call("dlgOpen", "ShowOpen") != "OK" {
		return
	}
	if path := Get("dlgOpen", "FileName"); path != "" {
		openFile(path)
	}
}

func mnuSaveAs_Click() {
	suggested := "Untitled.txt"
	if fileName != "" {
		suggested = filepath.Base(fileName)
	}
	Set("dlgSave", "FileName", suggested)
	if Call("dlgSave", "ShowSave") != "OK" {
		return
	}
	if path := Get("dlgSave", "FileName"); path != "" {
		writeFile(path)
	}
}

func mnuSave_Click() {
	if fileName == "" {
		mnuSaveAs_Click()
	} else {
		writeFile(fileName)
	}
}

func mnuExit_Click() {
	if confirmDiscard() {
		End()
	}
}

func mnuCut_Click() {
	sel := Get("txtDoc", "SelText")
	if sel == "" {
		return
	}
	clipboardPut(sel)
	Set("txtDoc", "SelText", "")
	status("Cut to the clipboard")
}

func mnuCopy_Click() {
	sel := Get("txtDoc", "SelText")
	if sel == "" {
		status("Nothing selected")
		return
	}
	clipboardPut(sel)
	status("Copied to the clipboard")
}

func mnuPaste_Click() {
	clip := clipboardGet()
	if clip == "" {
		status("The clipboard has no text")
		return
	}
	Set("txtDoc", "SelText", clip)
	status("Pasted")
}

func mnuSelectAll_Click() {
	Set("txtDoc", "SelStart", 0)
	Set("txtDoc", "SelLength", utf8.RuneCountInString(Get("txtDoc", "Text")))
	Call("txtDoc", "SetFocus")
}

func mnuFind_Click() {
	w := Input("Find what:")
	if w == "" {
		return
	}
	findWhat = w
	Set("txtDoc", "SelLength", 0)
	findNext()
}

func mnuFindNext_Click() {
	if findWhat == "" {
		mnuFind_Click()
	} else {
		findNext()
	}
}

func mnuReplace_Click() {
	what := Input("Replace what:")
	if what == "" {
		return
	}
	with := Input("Replace with:")
	text := Get("txtDoc", "Text")
	count := strings.Count(text, what)
	if count > 0 {
		Set("txtDoc", "Text", strings.ReplaceAll(text, what, with))
	}
	status(strconv.Itoa(count) + " replacement(s)")
}

func mnuTimeDate_Click() { Set("txtDoc", "SelText", time.Now().Format("15:04 2006-01-02")) }

func mnuFont_Click() {
	Set("dlgFont", "FontName", Get("txtDoc", "FontName"))
	Set("dlgFont", "FontSize", Get("txtDoc", "FontSize"))
	if Call("dlgFont", "ShowFont") != "OK" {
		return
	}
	Set("txtDoc", "FontName", Get("dlgFont", "FontName"))
	Set("txtDoc", "FontSize", Get("dlgFont", "FontSize"))
	status("Font: " + Get("txtDoc", "FontName") + " " + Get("txtDoc", "FontSize") + " pt")
}

func mnuWordCount_Click() {
	text := Get("txtDoc", "Text")
	lines := 0
	if text != "" {
		lines = strings.Count(text, "\n") + 1
	}
	chars := utf8.RuneCountInString(strings.NewReplacer("\r", "", "\n", "").Replace(text))
	msg := fmt.Sprintf("%d words, %d lines, %d characters", len(strings.Fields(text)), lines, chars)
	status(msg)
	MsgBox(msg)
}

func mnuAbout_Click() { MsgBox("Notepad - a RAD IDE example in Go\n(c) 2026 Musoftware - MIT License") }
