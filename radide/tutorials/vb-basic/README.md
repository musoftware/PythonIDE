# BASIC course (vb-basic): block format for the tutorial runner

24 Arabic lessons (`NN-slug.md`) for the IDE's own VB6 interpreter (`radide/runtimes/vbrun.py`), listed in
`course.json` (the shared tutorials format). The fenced blocks the runner/viewer must understand:

| Info string | Meaning | How to run it ("جرّبه") |
|---|---|---|
| ```` ```vb run ```` | console example: a standard module with `Sub Main` | project with `Module1.bas`, startup `Sub Main` |
| ```` ```vb form run ```` | form example: **VB6 `.frm` text** (`Begin VB.Form ... End`, then the form's code) | `parse_frm` + `_FrmConverter` from `radide/importers/vb6_import.py` -> `Form1.form` + `Form1.bas`, startup = the form (the same path as File > Import VB6) |
| ```` ```vb exercise ```` / ```` ```vb form exercise ```` | starter code (parses; usually not complete) | optional: open it as a project to edit |
| ```` ```vb solution ```` / ```` ```vb form solution ```` | the solution (hidden until clicked), runnable like `run` | same as `run` / `form run` |
| ```` ```text output ```` | expected Output-window text (`Debug.Print`) of the block just before it | display only |
| ```` ```quiz ```` | one JSON object: `question`, `choices`, `answer` (0-based), `explanation` | quiz widget |
| ```` ```vb ```` | plain snippet, not runnable | display only |

**Several files in one block:** lines `'#file: Name.ext` split a block into files, e.g. `Module1.bas` + `CPerson.cls`,
or `Form1.frm` + `CContact.cls`. `.frm` files become forms, everything else is added to `project.modules`
(`.cls` = class module). Without markers the whole block is `Module1.bas` (`run`) or `Form1.frm` (`form run`).
Reference implementation: `make_project()` in `tools/check_lessons.py` (about 25 lines; tutsys may copy it).

**Test comments:** an HTML comment `<!-- test: {...} -->` right before a block scripts the headless test (InputBox
answers, clicks, expected control properties, MsgBox prompts, an expected run-time error). It is invisible in
rendered Markdown; the viewer can ignore it.

## Testing

    python radide/tutorials/vb-basic/tools/check_lessons.py          # all lessons
    python radide/tutorials/vb-basic/tools/check_lessons.py 07 -v    # one lesson, list every block

Every `run`/`solution` block runs in its own process with the real runtime (Tk forms hidden, MsgBox/InputBox
scripted); `exercise` blocks are syntax-checked. A block with neither an output block nor a test comment fails.

## Interpreter gaps found while writing (examples avoid them)

- Doubles print with 17 significant digits (`200 * 0.14` -> `28.000000000000004`; VB6 prints `28`). `to_str` in
  `vbinterp.py` rounds to 15 *decimal places*, not 15 significant digits (`f"{v:.15g}"` would match VB6).
- No Overflow (error 6): `Dim i As Integer: i = 40000` is accepted.
- `Debug.Print a; b` does not add VB6's leading space before positive numbers (lessons use `&`).
- An unassigned `Function ... As Boolean` returns `Empty` (prints as an empty line) instead of `False`.
- `Replace(s, find, repl, start, count)` ignores `count`.
- Run time: `TextBox.PasswordChar` cannot be set from code (design-time value works); control-array elements have
  no `.Index` property and `Load ctl(n)` (new element at run time) is not supported.
- Text files are written in the ANSI code page like VB6, so Arabic text in files needs an Arabic system locale
  (lesson 19 says so; file examples use English data).
- `Class_Terminate` did not run when the last reference was released (not used in the lessons).
- The form designer has no UI to create a control array; arrays come from `.frm` files (lesson 16 says so).
