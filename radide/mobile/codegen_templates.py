"""New Project templates of the Mobile group (CONTRACTS 10.1) and the HelloMobile sample.

    flutter_app    Flutter App - one screen: app bar, text field, button, list
    flutter_tabs   Flutter App (tabs + drawer) - bottom navigation pages, drawer, FAB, a second screen
    hello_mobile   samples/HelloMobile - a contacts list screen + an edit form screen with navigation
    kivy_app       Python Kivy App - one screen (radide/languages/kivy_app.py)
"""
from __future__ import annotations

from pathlib import Path

from ..model import Control, Form, Project
from .codegen_common import ensure_types


def _form(name: str, title: str, device: str = "pixel") -> Form:
    ensure_types()
    f = Form()
    f.props["Name"] = name
    f.props["Text"] = title
    f.props["Device"] = device
    f.props["Orientation"] = "Portrait"
    f.props["Route"] = ""
    try:
        from .controls import ensure_mobile_props
        ensure_mobile_props(f.props)
    except Exception:  # noqa: BLE001 - designer module not available: a medium phone safe area
        f.props["Width"], f.props["Height"] = 412, 867
    return f


def _add(form: Form, ctype: str, name: str, x: int, y: int, w: int, h: int, parent: str = "", **props) -> Control:
    c = Control.from_dict({"type": ctype, "props": {"Name": name}})
    c.props.update({"Left": x, "Top": y, "Width": w, "Height": h, "Parent": parent})
    if not parent and x == 16 and w == int(form.props["Width"]) - 32:
        c.props["Anchor"] = "Top, Left, Right"          # full-width controls follow the phone's width
    if "Text" not in props and c.ctype.has_text:
        c.props["Text"] = name
    c.props.update(props)
    form.controls.append(c)
    return c


def _appbar(form: Form, title: str, actions: str = "", name: str = "AppBar1") -> Control:
    W = int(form.props["Width"])
    return _add(form, "AppBar", name, 0, 0, W, 56, Title=title, Text=title, Actions=actions, Dock="Top")


# =========================================================================== Flutter
def flutter_app() -> list[tuple[Form, str]]:
    f = _form("MainScreen", "My App")
    W = int(f.props["Width"])
    _appbar(f, "My App", "info")
    _add(f, "Label", "lblHello", 16, 72, W - 32, 32, Text="Welcome! Type your name and tap the button.",
         FontSize=11)
    _add(f, "MTextField", "txtName", 16, 112, W - 32, 56, Text="", Hint="Your name")
    _add(f, "Button", "btnHello", 16, 180, W - 32, 44, Text="Say hello", FontSize=11)
    _add(f, "MListView", "lstGreetings", 16, 240, W - 32, 360, Items="", ItemTemplate="title|subtitle")
    code = """// MainScreen - write your event handlers here (double-click a control in the designer).
// Controls are fields: lblHello.text = 'Hi'; txtName.text; lstGreetings.addItem('a|b');
// Screens: ShowForm('Form2') / CloseForm()   Dialogs: MsgBox('...'), Toast('...'), await InputBox('...')
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblHello.text = 'Welcome! Type your name and tap the button.';
  }

  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('Please type your name first');
      return;
    }
    final time = TimeOfDay.now().format(context);
    lstGreetings.addItem('Hello, $name!|said at $time');
    txtName.text = '';
  }

  void lstGreetings_Tap(RadEvent e) {
    MsgBox(lstGreetings.field(e.Index, 0), 'You tapped');
  }

  void AppBar1_Click(RadEvent e) {
    MsgBox('Made with RAD IDE and Flutter.', 'About');
  }
}
"""
    return [(f, code)]


def flutter_tabs() -> list[tuple[Form, str]]:
    f = _form("MainScreen", "My App")
    W, H = int(f.props["Width"]), int(f.props["Height"])
    _appbar(f, "My App", "search;more_vert")
    _add(f, "Drawer", "Drawer1", 0, 56, 280, H - 56 - 80, Text="My App", Items="Home:home;Settings:settings;About:info",
         Visible=True)
    nav = _add(f, "BottomNav", "BottomNav1", 0, H - 80, W, 80, Items="Home:home;Search:search;Profile:person",
               SelectedIndex=0, Dock="Bottom")
    nav.props["Anchor"] = "Bottom, Left, Right"
    page_h = H - 56 - 80
    for i, (pn, vis) in enumerate((("pnlHome", True), ("pnlSearch", False), ("pnlProfile", False))):
        _add(f, "Column", pn, 0, 56, W, page_h, Spacing=12, Align="Stretch", Padding=16, Visible=vis,
             Anchor="Top, Bottom, Left, Right")
    _add(f, "Label", "lblWelcome", 0, 0, W - 32, 32, "pnlHome", Text="Latest news", FontSize=14, FontBold=True)
    _add(f, "MListView", "lstNews", 0, 0, W - 32, 360, "pnlHome",
         Items="Flutter 3|New release|flutter_dash;RAD IDE|Mobile designer is here|phone_android;"
               "Tip|Double-click a control to write code|lightbulb",
         ItemTemplate="title|subtitle|icon")
    _add(f, "Button", "btnDetails", 0, 0, W - 32, 44, "pnlHome", Text="Open the details screen", FontSize=11)
    _add(f, "MTextField", "txtSearch", 0, 0, W - 32, 56, "pnlSearch", Text="", Hint="Search (press Enter)")
    _add(f, "MListView", "lstResults", 0, 0, W - 32, 400, "pnlSearch", Items="", ItemTemplate="title")
    _add(f, "MTextField", "txtUser", 0, 0, W - 32, 56, "pnlProfile", Text="", Hint="Your name")
    _add(f, "Switch", "swNews", 0, 0, W - 32, 48, "pnlProfile", Text="Send me news", Checked=True)
    _add(f, "MSlider", "sldSize", 0, 0, W - 32, 48, "pnlProfile", Minimum=10, Maximum=30, Value=16)
    _add(f, "Label", "lblSize", 0, 0, W - 32, 24, "pnlProfile", Text="Text size: 16", FontSize=11)
    _add(f, "Button", "btnSave", 0, 0, W - 32, 44, "pnlProfile", Text="Save", FontSize=11)
    _add(f, "Fab", "Fab1", W - 72, H - 80 - 72, 56, 56, Icon="add", Text="", Anchor="Bottom, Right")
    code = """// MainScreen - bottom navigation switches the pages (Column containers); the drawer and the
// floating action button show messages; btnDetails opens the second screen with ShowForm.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> _words = ['apple', 'banana', 'cherry', 'flutter', 'kotlin', 'python', 'dart'];

  void MainScreen_Load() {
    showPage(BottomNav1.selectedIndex);
  }

  void showPage(int index) {
    pnlHome.visible = index == 0;
    pnlSearch.visible = index == 1;
    pnlProfile.visible = index == 2;
  }

  void BottomNav1_Changed(RadEvent e) {
    showPage(e.Index);
  }

  void Drawer1_Tap(RadEvent e) {
    Toast('Drawer: ${e.Text}');
  }

  void AppBar1_Click(RadEvent e) {
    if (e.Action == 'search') {
      BottomNav1.selectedIndex = 1;
      showPage(1);
    } else {
      MsgBox('RAD IDE Flutter template', 'More');
    }
  }

  void Fab1_Click() {
    lstNews.addItem('New item|added at ${TimeOfDay.now().format(context)}|star');
    Toast('Item added');
  }

  void btnDetails_Click() {
    ShowForm('DetailsScreen', lstNews.count);
  }

  void txtSearch_Submitted(RadEvent e) {
    final q = txtSearch.text.trim().toLowerCase();
    lstResults.setItems(_words.where((w) => w.contains(q)));
  }

  void sldSize_Changed(RadEvent e) {
    lblSize.text = 'Text size: ${sldSize.value.round()}';
  }

  void btnSave_Click() {
    RadApp.data['user'] = txtUser.text;
    Toast('Saved ${txtUser.text} (news: ${swNews.checked ? 'on' : 'off'})');
  }
}
"""
    d = _form("DetailsScreen", "Details")
    W = int(d.props["Width"])
    _appbar(d, "Details", "", "AppBar1")
    _add(d, "Card", "cardInfo", 16, 72, W - 32, 140, Elevation=2)
    _add(d, "MIcon", "icoInfo", 16, 16, 40, 40, "cardInfo", Icon="info")
    _add(d, "Label", "lblInfo", 72, 16, W - 32 - 88, 100, "cardInfo", Text="...", FontSize=12)
    _add(d, "Button", "btnBack", 16, 232, W - 32, 44, Text="Back", FontSize=11)
    dcode = """// DetailsScreen - opened by ShowForm('DetailsScreen', value); FormArgs is that value.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'details_screen_designer.dart';

class DetailsScreenCode extends DetailsScreenDesigner {
  void DetailsScreen_Load() {
    final user = RadApp.data['user'] ?? 'guest';
    lblInfo.text = 'Hello $user!\\nThe home page has ${FormArgs ?? 0} news items.';
  }

  void btnBack_Click() {
    CloseForm();
  }
}
"""
    return [(f, code), (d, dcode)]


def hello_mobile() -> list[tuple[Form, str]]:
    """samples/HelloMobile: a contacts list (screen 1) and an edit form (screen 2)."""
    f = _form("ContactsScreen", "Contacts")
    W, H = int(f.props["Width"]), int(f.props["Height"])
    _appbar(f, "Hello Mobile", "info")
    _add(f, "MTextField", "txtFilter", 16, 68, W - 32, 56, Text="", Hint="Filter contacts")
    _add(f, "MListView", "lstContacts", 0, 132, W, H - 132,
         Items="Ada Lovelace|ada@example.com|person;Alan Turing|alan@example.com|person;"
               "Grace Hopper|grace@example.com|person",
         ItemTemplate="title|subtitle|icon", Anchor="Top, Bottom, Left, Right")
    _add(f, "Fab", "fabAdd", W - 72, H - 72, 56, 56, Icon="add", Text="", Anchor="Bottom, Right")
    code = """// ContactsScreen - a list of contacts. Tap a contact to edit it, + adds one.
// ShowForm('EditScreen', index) opens the second screen and waits for its result (CloseForm(result)).
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'contacts_screen_designer.dart';

class ContactsScreenCode extends ContactsScreenDesigner {
  final List<String> _all = [];

  void ContactsScreen_Load() {
    _all.addAll(lstContacts.items);
  }

  void _refresh() {
    final q = txtFilter.text.trim().toLowerCase();
    lstContacts.setItems(_all.where((c) => c.toLowerCase().contains(q)));
  }

  void txtFilter_Changed(RadEvent e) {
    _refresh();
  }

  Future<void> lstContacts_Tap(RadEvent e) async {
    final index = _all.indexOf(lstContacts.items[e.Index]);
    final result = await ShowForm('EditScreen', _all[index]);
    if (result is String) {
      _all[index] = result;
      _refresh();
      Toast('Contact saved');
    }
  }

  Future<void> fabAdd_Click() async {
    final result = await ShowForm('EditScreen', '');
    if (result is String) {
      _all.add(result);
      _refresh();
      Toast('Contact added');
    }
  }

  void AppBar1_Click(RadEvent e) {
    MsgBox('${_all.length} contacts. Made with RAD IDE + Flutter.', 'Hello Mobile');
  }
}
"""
    e = _form("EditScreen", "Edit contact")
    W = int(e.props["Width"])
    _appbar(e, "Edit contact", "delete")
    _add(e, "Column", "colForm", 0, 56, W, 420, Spacing=12, Align="Stretch", Padding=16)
    _add(e, "MTextField", "txtName", 0, 0, W - 32, 56, "colForm", Text="", Hint="Name")
    _add(e, "MTextField", "txtEmail", 0, 0, W - 32, 56, "colForm", Text="", Hint="E-mail")
    _add(e, "Switch", "swFavorite", 0, 0, W - 32, 48, "colForm", Text="Favorite")
    _add(e, "Row", "rowButtons", 0, 0, W - 32, 48, "colForm", Spacing=12, Align="Start", Padding=0)
    _add(e, "Button", "btnSave", 0, 0, 140, 44, "rowButtons", Text="Save", FontSize=11)
    _add(e, "Button", "btnCancel", 0, 0, 140, 44, "rowButtons", Text="Cancel", FontSize=11)
    _add(e, "Label", "lblStatus", 0, 0, W - 32, 24, "colForm", Text="", FontSize=10)
    ecode = """// EditScreen - FormArgs is the contact ("name|email|icon", '' = new); CloseForm(result) returns it.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'edit_screen_designer.dart';

class EditScreenCode extends EditScreenDesigner {
  void EditScreen_Load() {
    final parts = (FormArgs as String? ?? '').split('|');
    txtName.text = parts.isNotEmpty ? parts[0] : '';
    txtEmail.text = parts.length > 1 ? parts[1] : '';
    swFavorite.checked = parts.length > 2 && parts[2] == 'star';
    lblStatus.text = txtName.text.isEmpty ? 'New contact' : 'Editing ${txtName.text}';
  }

  void btnSave_Click() {
    if (txtName.text.trim().isEmpty) {
      MsgBox('Please type a name.');
      return;
    }
    CloseForm('${txtName.text.trim()}|${txtEmail.text.trim()}|${swFavorite.checked ? 'star' : 'person'}');
  }

  void btnCancel_Click() {
    CloseForm();
  }

  Future<void> AppBar1_Click(RadEvent e) async {
    if (await Confirm('Discard the changes?')) {
      CloseForm();
    }
  }
}
"""
    return [(f, code), (e, ecode)]


FLUTTER_TEMPLATES = {"flutter_app": flutter_app, "flutter_tabs": flutter_tabs, "hello_mobile": hello_mobile}


def build_flutter_project(plugin, folder: Path, name: str, template: str = "flutter_app") -> Project:
    """Create a complete Flutter project (no platform folders yet - they come with the first run)."""
    folder = Path(folder)
    (folder / "lib").mkdir(parents=True, exist_ok=True)
    forms = FLUTTER_TEMPLATES.get(template, flutter_app)()
    project = Project(folder, name, plugin.id)
    project.extra["mobile"] = {"device": "windows"}
    for form, code in forms:
        form.save(project.form_path(form.name))
        (folder / plugin.code_file(form.name)).write_text(code, encoding="utf-8")
        (folder / plugin.designer_file(form.name)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
        project.forms.append(form.name)
    project.startup = forms[0][0].name
    project.save()
    plugin.write_project_files(project)
    return project


# =========================================================================== Kivy
def kivy_app() -> list[tuple[Form, str]]:
    f = _form("MainScreen", "My Kivy App", "small_phone")
    W = int(f.props["Width"])
    _appbar(f, "My Kivy App", "info")
    _add(f, "Label", "lblHello", 16, 72, W - 32, 32, Text="Type your name and tap the button.", FontSize=11)
    _add(f, "MTextField", "txtName", 16, 112, W - 32, 48, Text="", Hint="Your name")
    _add(f, "Button", "btnHello", 16, 172, W - 32, 44, Text="Say hello", FontSize=11)
    _add(f, "Switch", "swShout", 16, 228, W - 32, 40, Text="Shout")
    _add(f, "MListView", "lstGreetings", 16, 280, W - 32, 280, Items="", ItemTemplate="title")
    return [(f, None)]
