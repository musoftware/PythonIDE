// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in Go (RAD IDE GUI Bridge; Build > Publish makes an exe).
//
// The database is contacts.json (encoding/json, indented so it is easy to read), loaded at start-up and
// written after every change. Shows: a ListBox filled from a slice of structs, a details GroupBox
// (TextBox / ComboBox / CheckBox), add / edit / delete / search, sort.Slice, validation, error values.
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"sort"
	"strings"
)

const dbFile = "contacts.json"

type Contact struct {
	ID       int    `json:"id"`
	Name     string `json:"name"`
	Phone    string `json:"phone"`
	Email    string `json:"email"`
	Group    string `json:"group"`
	Favorite bool   `json:"favorite"`
}

func (c *Contact) row() string {
	star := ""
	if c.Favorite {
		star = "* "
	}
	return fmt.Sprintf("%s%s  (%s)", star, c.Name, c.Phone)
}

func (c *Contact) matches(f string) bool {
	f = strings.ToLower(strings.TrimSpace(f))
	return f == "" || strings.Contains(strings.ToLower(c.Name+"|"+c.Phone+"|"+c.Email+"|"+c.Group), f)
}

var (
	contacts []*Contact // the database
	shown    []*Contact // the rows of the list
	current  *Contact   // nil = a new contact
)

// ------------------------------------------------------------------ database
func loadDB() error {
	data, err := os.ReadFile(dbFile)
	if errors.Is(err, fs.ErrNotExist) {
		contacts = []*Contact{
			{1, "Ahmed Hassan", "010 1234 5678", "ahmed@example.com", "Family", true},
			{2, "Sara Ali", "011 2222 3333", "sara@example.com", "Friends", false},
			{3, "Musoftware Support", "02 555 0100", "support@example.com", "Work", false},
		}
		return saveDB()
	}
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &contacts)
}

func saveDB() error {
	data, err := json.MarshalIndent(contacts, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(dbFile, data, 0o644)
}

// ------------------------------------------------------------------ UI
func fillList(filter string) {
	shown = shown[:0]
	for _, c := range contacts {
		if c.matches(filter) {
			shown = append(shown, c)
		}
	}
	sort.Slice(shown, func(i, j int) bool {
		if shown[i].Favorite != shown[j].Favorite {
			return shown[i].Favorite
		}
		return strings.ToLower(shown[i].Name) < strings.ToLower(shown[j].Name)
	})
	Call("lstContacts", "Clear")
	for _, c := range shown {
		Call("lstContacts", "AddItem", c.row())
	}
	Set("lblCount", "Caption", fmt.Sprintf("%d of %d contacts", len(shown), len(contacts)))
}

func showContact(c *Contact) {
	current = c
	v := c
	if v == nil {
		v = &Contact{Group: "Family"}
	}
	Set("txtName", "Text", v.Name)
	Set("txtPhone", "Text", v.Phone)
	Set("txtEmail", "Text", v.Email)
	Set("cboGroup", "Text", v.Group)
	fav, enabled, caption := 0, "False", "New contact"
	if v.Favorite {
		fav = 1
	}
	if c != nil {
		enabled, caption = "True", "Details"
	}
	Set("chkFavorite", "Value", fav)
	Set("btnDelete", "Enabled", enabled)
	Set("grpDetails", "Caption", caption)
}

func selectContact(c *Contact) {
	for i, s := range shown {
		if s == c {
			Set("lstContacts", "ListIndex", i)
		}
	}
	showContact(c)
}

func status(s string) { Set("sbStatus", "Text", s) }

// ------------------------------------------------------------------ events
func frmContacts_Load() {
	if err := loadDB(); err != nil {
		MsgBox(dbFile + " cannot be read: " + err.Error())
	}
	fillList("")
	showContact(nil)
	status(fmt.Sprintf("Database: %s (%d records)", dbFile, len(contacts)))
}

func lstContacts_SelectedIndexChanged() {
	if row := int(GetNum("lstContacts", "ListIndex")); row >= 0 && row < len(shown) {
		showContact(shown[row])
	}
}

func btnNew_Click() {
	showContact(nil)
	Call("txtName", "SetFocus")
	status("Type the new contact and press Save")
}

func btnSave_Click() {
	name, email := strings.TrimSpace(Get("txtName", "Text")), strings.TrimSpace(Get("txtEmail", "Text"))
	if name == "" {
		MsgBox("Please type a name.")
		return
	}
	if email != "" && !strings.Contains(email, "@") {
		MsgBox("The e-mail address needs an @.")
		return
	}
	isNew := current == nil
	c := current
	if isNew {
		maxID := 0
		for _, x := range contacts {
			if x.ID > maxID {
				maxID = x.ID
			}
		}
		c = &Contact{ID: maxID + 1}
		contacts = append(contacts, c)
	}
	c.Name, c.Phone, c.Email = name, strings.TrimSpace(Get("txtPhone", "Text")), email
	c.Group = Get("cboGroup", "Text")
	if c.Group == "" {
		c.Group = "Other"
	}
	c.Favorite = GetNum("chkFavorite", "Value") == 1
	if err := saveDB(); err != nil {
		MsgBox("Save failed: " + err.Error())
		return
	}
	fillList("")
	selectContact(c)
	if isNew {
		status("Added " + c.Name)
	} else {
		status("Updated " + c.Name)
	}
}

func btnDelete_Click() {
	if current == nil {
		return
	}
	if !strings.HasPrefix(strings.ToLower(Input("Delete "+current.Name+"? Type YES to confirm:")), "y") {
		return
	}
	name := current.Name
	for i, c := range contacts {
		if c == current {
			contacts = append(contacts[:i], contacts[i+1:]...)
			break
		}
	}
	if err := saveDB(); err != nil {
		MsgBox("Save failed: " + err.Error())
	}
	fillList("")
	showContact(nil)
	status("Deleted " + name)
}

func btnFind_Click() {
	f := Get("txtSearch", "Text")
	fillList(f)
	status(fmt.Sprintf("Search %q: %d found", f, len(shown)))
	if len(shown) == 1 {
		selectContact(shown[0])
	}
}

func txtSearch_KeyPress(e RadEvent) {
	if p := strings.Fields(e.Args); len(p) > 3 && (p[3] == "Return" || p[3] == "13") {
		btnFind_Click()
	}
}

func btnShowAll_Click() {
	Set("txtSearch", "Text", "")
	fillList("")
	status("All contacts")
}
