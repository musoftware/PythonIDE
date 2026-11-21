# PE / MFC Resource Workbench

RAD IDE opens Windows programs (`.exe`, `.dll`, `.ocx`, `.cpl`, 32-bit and 64-bit) built with C / C++
(Win32, MFC) to edit their **resources**, look at their **code** and see or change their **MFC event
handlers** (message maps). It is meant for your own programs, for programs you are allowed to change, and
for learning how Windows programs are built.

> **Scope.** The workbench edits resources and makes small in-place changes. It never adds code to a
> program: there are no code caves, no injected code, no hooks, no packers / unpackers, and nothing for
> licence checks, DRM or other protections. Every save writes a **new file**; the opened file is never
> changed silently, and any file that is replaced is first copied to `<file>.bak`.

Open it with **Tools > PE / MFC Resource Workbench...**, by opening an `.exe` / `.dll` (File > Open,
Solution Explorer), or with **Open With > PE / MFC Resource Workbench** in Solution Explorer.

| Package | What |
|---|---|
| `radide/pe/image.py` | PE32 / PE32+ reader / writer: sections, data directories, imports (also delay-load), exports, base relocations (read / rebuild), add / resize sections, Authenticode removal, PE checksum. No `pefile` needed. |
| `radide/pe/resources.py` | resource tree read / rebuild; codecs for DIALOG / DIALOGEX, MENU / MENUEX, string tables, accelerators, VERSIONINFO, icon / cursor groups (.ico / .cur), bitmaps (.bmp), MFC `RT_TOOLBAR` (241) and `RT_DLGINIT` (240). Byte-exact round trips. |
| `radide/pe/rc.py` | export to `.rc` + `res/` files, import `.rc` (dialogs incl. LTEXT / PUSHBUTTON / EDITTEXT ... shortcuts, menus, strings, accelerators, version, icons, cursors, bitmaps, toolbars, user types, `#define` / `#include "x.h"`) |
| `radide/pe/code.py` | Capstone x86 / x64 analysis: functions (entry, exports, x64 `.pdata`, call targets, callbacks, MFC handlers), import thunks, strings, cross references, commented listings |
| `radide/pe/asm.py` | assembler: Keystone when installed (`pip install keystone-engine`), else a built-in subset |
| `radide/pe/mfc.py` | MFC message maps: finder, RTTI class names, base-class chain, entry descriptions (`ON_BN_CLICKED`, `ON_COMMAND`, `ON_EN_CHANGE`, `ON_CONTROL_RANGE`, `ON_UPDATE_COMMAND_UI`, `ON_NOTIFY`, `ON_MESSAGE`, `ON_WM_*`) |
| `radide/pe/document.py` | `PeDocument`: edits with undo / redo, save-as with backups |
| `radide/pe/ui.py` | the workbench tab (Qt) |
| `radide/features/pe_workbench.py` | menu, file association, Open With, Save / Undo integration |

## Resources

The **Resources** tab shows the tree *type > name > language*. Editors:

* **Dialog designer** - the template at its real size (dialog units converted with the dialog font). Drag a
  control to move it, drag its blue corner to resize it (snapped to dialog units), Toolbox to add Button,
  Check box, Radio, Group box, Label, Edit, Combo box, List box, Picture; Delete Control. Properties:
  caption, ID, class, position / size, style / extended style (hex) with Visible / Disabled / Tab stop / Group
  check boxes; with nothing selected the dialog's own caption, size, style and font. A green dot marks controls
  that have an MFC event handler. **Double-click a control** to see its handler's disassembly (like VB's code
  window). *Preview (Windows)* shows the template with Windows itself.
* **Menu** - tree with Text / ID / flags and the MFC handler of each command; add items, submenus,
  separators, move, delete, Apply. (The IDE's `menu_editor.py` edits RAD forms' MenuStrip items by *name*;
  resource menus need numeric IDs and flags, so the workbench has its own tree.)
* **String table** (all blocks of one language), **Accelerators** (`Ctrl+Shift+F5`, `Alt+X`, `"a"`),
  **Version** (file / product version and the StringFileInfo values), **MFC toolbar** (button order),
  **MFC dialog init** (combo / list box strings).
* **Icons / cursors / bitmaps / PNG** - preview, *Replace from File...* (`.ico` / `.cur` / `.bmp` / `.png`),
  *Export...*.
* **Manifest / HTML** - text editor. **Anything else** (RCDATA, custom types) - hex editor.

Toolbar: Add Resource (from `.ico` / `.cur` / `.bmp` / any file), Delete Resource, Copy to Language
(language variants, for example an Arabic `0x401` copy of a dialog), Export .rc / Import .rc.

When the resources no longer fit in their section, `.rsrc` is rebuilt as a new last section; otherwise it is
rewritten in place.

## Code

Functions (MFC handlers first, in green), the disassembly of the selected function with comments for imports
(`USER32!SetDlgItemTextW`), strings and function names, *Called From* (cross references), Imports and Strings
lists, *Go to address / name*, *Follow* (double-click a call), *Rename...*.

**Edit Instruction...** assembles new code at an address. It must fit in the instructions it replaces (same size
or smaller, the rest becomes NOPs); a bigger edit is refused with a message. *NOP Instruction* blanks one
instruction. Relocation entries inside a patched range are dropped (otherwise Windows would change the new bytes
when it loads the program at another address).

**Decompile (Ghidra)** shows pseudo-C for the current function when Ghidra is installed (the Ghidra that the
EXE importer / firmware tools find, `radide/firmware/analysis/ghidra.py`).

## MFC events

MFC stores each class's event table in the program:

```c
struct AFX_MSGMAP_ENTRY { UINT nMessage, nCode, nID, nLastID; UINT_PTR nSig; AFX_PMSG pfn; };  // 24 / 32 bytes
struct AFX_MSGMAP { const AFX_MSGMAP* (*pfnGetBaseMap)(); const AFX_MSGMAP_ENTRY* lpEntries; };
```

The finder scans the data sections for `AFX_MSGMAP` structures whose entries point into code and end with a
zero entry, follows `pfnGetBaseMap` to the base class (or notes an MFC DLL import), and names the class from the
RTTI of the vtable that holds `GetMessageMap()` (base classes without a vtable of their own are named from a
derived class's RTTI base list and marked *name guessed*). A dialog is linked to the class whose handlers cover
most of its control IDs (you can pick another class in the designer).

Edits:

* **Retarget Handler** - point an entry at another *existing* function (pick one of the same kind, for example
  another BN_CLICKED handler).
* **Remove Entry** - the rest of the table moves up; the freed slot is remembered.
* **Add Entry** - only where a removal freed a slot in this session. The table is never moved or enlarged.
* Relocations of the table are kept right (removed / added with the entries).

## Saving

*Save As...* (or File > Save) writes `<name>_edited.exe` by default. Saving over an existing file copies it to
`<file>.bak` first. The digital signature is removed (it is invalid after any change; you are told), the PE
checksum is recomputed, and the relocation table is rebuilt when entries changed. Undo / Redo cover every edit.

## Tests

`samples/Tests/PE/MfcResources/`:

* `src/` + `build.py` - **MiniMfc**, a dialog program built with MSVC (x86 and x64; `prebuilt/*.pe`). It
  re-creates MFC's message maps (same memory layout, `DECLARE_MESSAGE_MAP`, RTTI, the dispatcher) so that
  map edits change what the program really does, without needing the MFC libraries.
* `test_pe_core.py` - parse, edit dialog / string / menu / version / accelerators, retarget / remove / add map
  entries, instruction patch limits, undo / redo, save, re-parse, `.rc` round trip, and **runs** the edited
  programs (`winrun.py`): the new caption shows, Button1 runs Button2's handler, the added entry handles a new
  menu command, the original is unchanged.
* `qa_pe_workbench_ide.py` - the workbench inside the IDE (offscreen, `RADIDE-TEST` settings, `widget.grab()`).

## Limits

* Adding a message-map entry needs a slot freed by a removal in the same session.
* Instruction edits cannot grow; no new code or sections are added for code.
* The `.rc` importer is built in (no `rc.exe` needed) and covers the usual statements; MFC's special `DLGINIT`
  syntax is imported as plain data words.
* MFC programs linked with the MFC DLL: handlers are found; base classes inside the DLL are shown as imports.
* .NET assemblies: resources only.
