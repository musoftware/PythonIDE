// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in C# whose database is an XML file (contacts.xml) handled with LINQ to XML
// (RAD IDE GUI Bridge; Build > Publish = native WinForms exe - System.Xml.Linq is part of .NET everywhere).
//
// Shows: a ListBox filled from a List<Contact>, a details GroupBox with TextBox / ComboBox / CheckBox,
// add / edit / delete / search (LINQ queries), validation, XML load / save with error handling.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml.Linq;

public class Contact
{
    public int Id;
    public string Name = "", Phone = "", Email = "", Group = "Family";
    public bool Favorite;
    public override string ToString() => (Favorite ? "* " : "") + $"{Name}  ({Phone})";
}

public static partial class frmContacts
{
    const string DbFile = "contacts.xml";
    static List<Contact> all = new List<Contact>();
    static List<Contact> shown = new List<Contact>();     // the rows of the list (it can be filtered)
    static Contact current;                                // null = a new contact

    // ------------------------------------------------------------------ database
    static void Load()
    {
        all.Clear();
        if (!File.Exists(DbFile))
        {
            all.Add(new Contact { Id = 1, Name = "Ahmed Hassan", Phone = "010 1234 5678", Email = "ahmed@example.com", Group = "Family", Favorite = true });
            all.Add(new Contact { Id = 2, Name = "Sara Ali", Phone = "011 2222 3333", Email = "sara@example.com", Group = "Friends" });
            all.Add(new Contact { Id = 3, Name = "Musoftware Support", Phone = "02 555 0100", Email = "support@example.com", Group = "Work" });
            Save();
            return;
        }
        var doc = XDocument.Load(DbFile);
        all = doc.Root.Elements("contact").Select(x => new Contact
        {
            Id = (int)x.Attribute("id"),
            Name = (string)x.Element("name") ?? "",
            Phone = (string)x.Element("phone") ?? "",
            Email = (string)x.Element("email") ?? "",
            Group = (string)x.Element("group") ?? "Other",
            Favorite = (bool?)x.Attribute("favorite") ?? false,
        }).ToList();
    }

    static void Save()
    {
        var doc = new XDocument(new XElement("contacts",
            all.Select(c => new XElement("contact",
                new XAttribute("id", c.Id), new XAttribute("favorite", c.Favorite),
                new XElement("name", c.Name), new XElement("phone", c.Phone),
                new XElement("email", c.Email), new XElement("group", c.Group)))));
        doc.Save(DbFile);
    }

    // ------------------------------------------------------------------ UI
    static void FillList(string filter)
    {
        string f = filter.Trim();
        shown = all.Where(c => f == "" || new[] { c.Name, c.Phone, c.Email, c.Group }
                        .Any(v => v.IndexOf(f, StringComparison.CurrentCultureIgnoreCase) >= 0))
                   .OrderByDescending(c => c.Favorite).ThenBy(c => c.Name, StringComparer.CurrentCultureIgnoreCase)
                   .ToList();
        lstContacts.Clear();
        foreach (var c in shown) lstContacts.AddItem(c.ToString());
        lblCount.Caption = f == "" ? $"{shown.Count} contacts" : $"{shown.Count} of {all.Count} contacts match";
    }

    static void ShowContact(Contact c)
    {
        current = c;
        c = c ?? new Contact();
        txtName.Text = c.Name;
        txtPhone.Text = c.Phone;
        txtEmail.Text = c.Email;
        cboGroup.Text = c.Group;
        chkFavorite.Value = c.Favorite ? "1" : "0";
        btnDelete.Enabled = current != null;
        grpDetails.Caption = current != null ? "Details" : "New contact";
    }

    static void Select(Contact c)
    {
        int row = shown.IndexOf(c);
        if (row >= 0) lstContacts.ListIndex = row;
        ShowContact(c);
    }

    // ------------------------------------------------------------------ events
    static void frmContacts_Load(RadEvent e)
    {
        try
        {
            Load();
            sbStatus.Text = $"Database: {Path.GetFullPath(DbFile)} ({all.Count} records)";
        }
        catch (Exception ex)
        {
            MsgBox($"{DbFile} cannot be read: {ex.Message}");
        }
        FillList("");
        ShowContact(null);
    }

    static void lstContacts_SelectedIndexChanged(RadEvent e)
    {
        int row = lstContacts.ListIndex;
        if (row >= 0 && row < shown.Count) ShowContact(shown[row]);
    }

    static void btnNew_Click(RadEvent e)
    {
        ShowContact(null);
        txtName.SetFocus();
        sbStatus.Text = "Type the new contact and press Save";
    }

    static void btnSave_Click(RadEvent e)
    {
        string name = txtName.Text.Trim(), email = txtEmail.Text.Trim();
        if (name == "") { MsgBox("Please type a name."); return; }
        if (email != "" && !email.Contains("@")) { MsgBox("The e-mail address needs an @."); return; }
        bool isNew = current == null;
        var c = current ?? new Contact { Id = all.Count == 0 ? 1 : all.Max(x => x.Id) + 1 };
        c.Name = name;
        c.Phone = txtPhone.Text.Trim();
        c.Email = email;
        c.Group = cboGroup.Text == "" ? "Other" : cboGroup.Text;
        c.Favorite = chkFavorite.Value == "1";
        if (isNew) all.Add(c);
        try { Save(); }
        catch (Exception ex) { MsgBox($"Save failed: {ex.Message}"); return; }
        FillList("");
        Select(c);
        sbStatus.Text = (isNew ? "Added " : "Updated ") + c.Name;
    }

    static void btnDelete_Click(RadEvent e)
    {
        if (current == null) return;
        if (!InputBox($"Delete {current.Name}? Type YES to confirm:").StartsWith("y", StringComparison.OrdinalIgnoreCase))
            return;
        string name = current.Name;
        all.Remove(current);
        Save();
        FillList("");
        ShowContact(null);
        sbStatus.Text = "Deleted " + name;
    }

    static void btnFind_Click(RadEvent e)
    {
        FillList(txtSearch.Text);
        sbStatus.Text = $"Search \"{txtSearch.Text}\": {shown.Count} found";
        if (shown.Count == 1) Select(shown[0]);
    }

    static void txtSearch_KeyPress(RadEvent e)
    {
        string[] a = e.Args.Split(' ');
        if (a.Length > 3 && (a[3] == "Return" || a[3] == "13")) btnFind_Click(e);
    }

    static void btnShowAll_Click(RadEvent e)
    {
        txtSearch.Text = "";
        FillList("");
        sbStatus.Text = "All contacts";
    }
}
