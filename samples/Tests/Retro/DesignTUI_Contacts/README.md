# Contacts - a DOS Text-Mode Forms App (FreeBASIC)

A small contacts program drawn in RAD IDE's Text-Mode Designer and generated as QBasic-syntax code
(`MAIN.BAS`, built with FreeBASIC `-lang qb` for DOS, run in DOSBox-X).

* `Main.tform` - the main screen: menu bar (File: New contact, Exit; Help: About), a window with Name / Phone text
  boxes, a Favourite check box, a Group frame with three option buttons, the contacts list box, Add / Clear buttons,
  a progress bar (number of contacts), an information label and a status bar.
* `About.tform` - the second screen (Help > About), OK returns (it is also the Cancel button: Esc).
* `Splash.ans` - the splash screen shown for 3 seconds before the main screen (original ANSI art, CC0, SAUCE
  record).
* `MAIN.BAS` - generated; the event code is in the USER CODE regions (btnAdd, btnClear, lstContacts, the menu
  items, btnBack) and survives every regeneration.

Open the folder in RAD IDE, open `Main.tform` and press F5 (or **Build && Run in DOSBox-X** in the designer's tool
bar). Keys: type a name, Tab, a phone number, Alt+A adds it; Alt+L clears; F10 / Alt+F / Alt+H open the menus;
Esc quits. The mouse works too.

Tested by `samples/Tests/Retro/DesignTextMode/test_dosbox.py`.
