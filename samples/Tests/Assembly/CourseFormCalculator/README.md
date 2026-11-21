# CourseFormCalculator

**asm-nasm, x64, GUI Bridge** - the calculator of lesson 12 of the Arabic Assembly course
(`radide/tutorials/assembly/12-gui-form.md`), created by its "جرّبه" button: Form1 with `txtA`, `txtB`,
`btnAdd`, `btnMul` and `lblResult`; the handlers in `Form1.asm` read the text boxes with `rad_get_int`, compute
with `add` / `imul` and show the result with `rad_set_int`.

F5 runs it; `samples/Tests/Assembly/CourseTests/test_course_forms.py` drives this form (and the other forms of
the lesson) over the bridge protocol: 6 and 7 give 13 and 42.
