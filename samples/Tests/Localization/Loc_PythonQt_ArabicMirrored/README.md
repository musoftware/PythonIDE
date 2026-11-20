# Loc_PythonQt_ArabicMirrored

**python-qt** - VB-style **form localization** (`Localizable = True`): `Form1` and the user control `AddressBox`
(used twice) have resource tables for **Arabic** (`ar`, RightToLeft + RightToLeftLayout = the whole form is
mirrored) and **French** (`fr`). Save writes them as `Form1.ar.resx.json`, `Form1.fr.resx.json`,
`AddressBox.ar.resx.json` ... next to the forms.

**What it tests:** the generated program picks the language at start-up (`RADIDE_LANG` environment variable,
else a `language.txt` file next to the program, else the Windows UI language), translates Text / ToolTip / Items
and the user controls' Caption property, mirrors the layout for Arabic (controls placed from the right edge,
anchors kept, text right-aligned - inside the user controls too) and switches live with
`self.ApplyLanguage("fr")` (button *Switch language*: default -> ar -> fr).

**Try it:** F5 shows your Windows language (English -> default). To see Arabic: put `ar` in a file
`language.txt` in this folder (or `set RADIDE_LANG=ar` before running), or click *Switch language*.
In the designer: select the form, set **Language = Arabic (ar)** in the Properties window - the designer shows
the Arabic texts mirrored; what you type in Text is stored for Arabic only. *Format > Localization Strings...*
shows all languages in one table (add / remove languages, RTL / Mirror per language, import a .resx.json).

*Origin:* built by the user-controls/localization agent's test script (Python (Qt / PySide6)).
