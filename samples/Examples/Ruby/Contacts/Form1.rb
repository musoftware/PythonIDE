# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Contacts - event handlers for Form1 (Ruby, GUI Bridge).
# Shows: CRUD with validation, a DataGridView (select a row to edit it), live search (TextChanged),
#        JSON persistence and CSV export in a module (ContactStore.rb), Arabic names, menus, MsgBox/InputBox.
require_relative "ContactStore"

$visible = []      # contact indexes in the grid order (the grid may be filtered by the search box)
$editing = nil     # index of the contact loaded into the fields

def status(text)
  ui.sbStatus.Text = text
end

def fields_contact
  ContactStore::Contact.new(name: ui.txtName.Text.strip, phone: ui.txtPhone.Text.strip,
                            email: ui.txtEmail.Text.strip, city: ui.txtCity.Text.strip)
end

def fill_grid
  Rad.call("grdContacts", "Clear")
  $visible = []
  ContactStore.search(ui.txtSearch.Text).each do |i, c|
    $visible << i
    Rad.call("grdContacts", "AddItem", i + 1, c.name, c.phone, c.email, c.city)   # one argument per cell
  end
  status("#{$visible.size} of #{ContactStore.all.size} contact(s)")
end

def clear_fields
  %w[txtName txtPhone txtEmail txtCity].each { |n| Rad.set(n, "Text", "") }
  $editing = nil
end

def Form1_Load(e)
  if ContactStore.all.empty?            # first run: a few example contacts (Arabic and English)
    [["أحمد علي", "+20 100 555 0101", "ahmed@example.com", "القاهرة"],
     ["Sara Hassan", "+20 122 555 0144", "sara@example.com", "Alexandria"],
     ["محمد إبراهيم", "+966 50 555 0199", "", "الرياض"]].each do |n, p, m, c|
      ContactStore.all << ContactStore::Contact.new(name: n, phone: p, email: m, city: c)
    end
    ContactStore.save
  end
  fill_grid
end

def cmdAdd_Click(e)
  c = fields_contact
  if (err = ContactStore.validate(c))
    msgbox(err)
    return
  end
  ContactStore.add(c)
  clear_fields
  fill_grid
  status("Added #{c.name}")
end

def grdContacts_SelectedIndexChanged(e)
  row = Rad.get_num("grdContacts", "Row") - 1          # row 0 is the header
  return if row.negative? || row >= $visible.size
  $editing = $visible[row]
  c = ContactStore.all[$editing]
  ui.txtName.Text = c.name
  ui.txtPhone.Text = c.phone
  ui.txtEmail.Text = c.email
  ui.txtCity.Text = c.city
end

def cmdUpdate_Click(e)
  return msgbox("Select a contact in the list first.") if $editing.nil?
  c = fields_contact
  if (err = ContactStore.validate(c))
    msgbox(err)
    return
  end
  ContactStore.update($editing, c)
  fill_grid
  status("Updated #{c.name}")
end

def cmdDelete_Click(e)
  return msgbox("Select a contact in the list first.") if $editing.nil?
  name = ContactStore.all[$editing].name
  return unless Rad.input("Type YES to delete #{name}").strip.upcase == "YES"
  ContactStore.delete($editing)
  clear_fields
  fill_grid
  status("Deleted #{name}")
end

def cmdClear_Click(e)
  clear_fields
end

def txtSearch_TextChanged(e)
  fill_grid
end

def mnuFileSave_Click(e)
  ContactStore.save
  status("Saved to #{ContactStore::FILE}")
end

def mnuFileExport_Click(e)
  File.write("contacts.csv", ContactStore.to_csv, encoding: "UTF-8")
  msgbox("Exported #{ContactStore.all.size} contact(s) to contacts.csv")
end

def mnuFileExit_Click(e)
  Rad.quit
end

def mnuHelpAbout_Click(e)
  msgbox("Contacts - a RAD IDE example in Ruby #{RUBY_VERSION}. (c) 2026 Musoftware - MIT License")
end
