// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in Java (RAD IDE GUI Bridge; Build > Publish = native Swing exe).
//
// The database is contacts.csv (RFC 4180 style: fields with commas or quotes are quoted), read with
// java.nio.file.Files and written after every change. Shows: a ListBox filled from a List<Contact>, a details
// GroupBox (TextBox / ComboBox / CheckBox), add / edit / delete / search with streams, validation, CSV
// parsing and IOException handling.
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class frmContacts extends frmContactsDesigner {
    static final Path DB = Paths.get("contacts.csv");

    static class Contact {
        int id;
        String name = "", phone = "", email = "", group = "Family";
        boolean favorite;

        String row() { return (favorite ? "* " : "") + name + "  (" + phone + ")"; }

        boolean matches(String f) {
            String s = f.toLowerCase();
            return s.isEmpty() || (name + "|" + phone + "|" + email + "|" + group).toLowerCase().contains(s);
        }
    }

    static List<Contact> all = new ArrayList<>();
    static List<Contact> shown = new ArrayList<>();
    static Contact current;                         // null = a new contact

    // ------------------------------------------------------------------ CSV database
    static String quote(String v) {
        return v.contains(",") || v.contains("\"") ? "\"" + v.replace("\"", "\"\"") + "\"" : v;
    }

    static List<String> parseCsvLine(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (inQuotes) {
                if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') { cur.append('"'); i++; }
                else if (c == '"') inQuotes = false;
                else cur.append(c);
            } else if (c == '"') inQuotes = true;
            else if (c == ',') { out.add(cur.toString()); cur.setLength(0); }
            else cur.append(c);
        }
        out.add(cur.toString());
        return out;
    }

    static Contact make(int id, String name, String phone, String email, String group, boolean fav) {
        Contact c = new Contact();
        c.id = id; c.name = name; c.phone = phone; c.email = email; c.group = group; c.favorite = fav;
        return c;
    }

    static void load() throws IOException {
        all.clear();
        if (!Files.exists(DB)) {
            all.add(make(1, "Ahmed Hassan", "010 1234 5678", "ahmed@example.com", "Family", true));
            all.add(make(2, "Sara Ali", "011 2222 3333", "sara@example.com", "Friends", false));
            all.add(make(3, "Musoftware Support", "02 555 0100", "support@example.com", "Work", false));
            save();
            return;
        }
        for (String line : Files.readAllLines(DB, StandardCharsets.UTF_8)) {
            List<String> f = parseCsvLine(line);
            if (f.size() < 6 || !f.get(0).matches("\\d+")) continue;          // header / broken line
            all.add(make(Integer.parseInt(f.get(0)), f.get(1), f.get(2), f.get(3), f.get(4), f.get(5).equals("1")));
        }
    }

    static void save() throws IOException {
        List<String> lines = new ArrayList<>();
        lines.add("id,name,phone,email,group,favorite");
        for (Contact c : all)
            lines.add(c.id + "," + quote(c.name) + "," + quote(c.phone) + "," + quote(c.email) + "," + quote(c.group)
                      + "," + (c.favorite ? 1 : 0));
        Files.write(DB, lines, StandardCharsets.UTF_8);
    }

    // ------------------------------------------------------------------ UI
    static void fillList(String filter) {
        shown = all.stream().filter(c -> c.matches(filter.trim()))
                   .sorted(Comparator.comparing((Contact c) -> !c.favorite).thenComparing(c -> c.name.toLowerCase()))
                   .collect(Collectors.toList());
        lstContacts.clear();
        for (Contact c : shown) lstContacts.addItem(c.row());
        lblCount.setCaption(shown.size() + " of " + all.size() + " contacts");
    }

    static void showContact(Contact c) {
        current = c;
        Contact v = c != null ? c : new Contact();
        txtName.setText(v.name);
        txtPhone.setText(v.phone);
        txtEmail.setText(v.email);
        cboGroup.setText(v.group);
        chkFavorite.setValue(v.favorite ? 1 : 0);
        btnDelete.setEnabled(c != null);
        grpDetails.setCaption(c != null ? "Details" : "New contact");
    }

    static void select(Contact c) {
        int row = shown.indexOf(c);
        if (row >= 0) lstContacts.setListIndex(row);
        showContact(c);
    }

    // ------------------------------------------------------------------ events
    static void frmContacts_Load(RadEvent e) {
        try {
            load();
            sbStatus.setText("Database: " + DB.toAbsolutePath() + " (" + all.size() + " records)");
        } catch (IOException ex) {
            msgbox("contacts.csv cannot be read: " + ex.getMessage());
        }
        fillList("");
        showContact(null);
    }

    static void lstContacts_SelectedIndexChanged(RadEvent e) {
        int row = lstContacts.getListIndex();
        if (row >= 0 && row < shown.size()) showContact(shown.get(row));
    }

    static void btnNew_Click(RadEvent e) {
        showContact(null);
        txtName.setFocus();
        sbStatus.setText("Type the new contact and press Save");
    }

    static void btnSave_Click(RadEvent e) {
        String name = txtName.getText().trim(), email = txtEmail.getText().trim();
        if (name.isEmpty()) { msgbox("Please type a name."); return; }
        if (!email.isEmpty() && !email.contains("@")) { msgbox("The e-mail address needs an @."); return; }
        boolean isNew = current == null;
        Contact c = isNew ? new Contact() : current;
        if (isNew) c.id = all.stream().mapToInt(x -> x.id).max().orElse(0) + 1;
        c.name = name;
        c.phone = txtPhone.getText().trim();
        c.email = email;
        c.group = cboGroup.getText().isEmpty() ? "Other" : cboGroup.getText();
        c.favorite = chkFavorite.getValue().equals("1");
        if (isNew) all.add(c);
        try {
            save();
        } catch (IOException ex) {
            msgbox("Save failed: " + ex.getMessage());
            return;
        }
        fillList("");
        select(c);
        sbStatus.setText((isNew ? "Added " : "Updated ") + c.name);
    }

    static void btnDelete_Click(RadEvent e) {
        if (current == null) return;
        if (!input("Delete " + current.name + "? Type YES to confirm:").toLowerCase().startsWith("y")) return;
        String name = current.name;
        all.remove(current);
        try {
            save();
        } catch (IOException ex) {
            msgbox("Save failed: " + ex.getMessage());
        }
        fillList("");
        showContact(null);
        sbStatus.setText("Deleted " + name);
    }

    static void btnFind_Click(RadEvent e) {
        fillList(txtSearch.getText());
        sbStatus.setText("Search \"" + txtSearch.getText() + "\": " + shown.size() + " found");
        if (shown.size() == 1) select(shown.get(0));
    }

    static void txtSearch_KeyPress(RadEvent e) {
        String[] a = e.args.split(" ");
        if (a.length > 3 && (a[3].equals("Return") || a[3].equals("10") || a[3].equals("13"))) btnFind_Click(e);
    }

    static void btnShowAll_Click(RadEvent e) {
        txtSearch.setText("");
        fillList("");
        sbStatus.setText("All contacts");
    }
}
