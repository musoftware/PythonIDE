# Emu8086Structs

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: structures and conditional
assembly in RAD IDE's own 8086 emulator (radide/emu8086), and the export to a real DOS program.

**What it shows:**

* `student struc` ... `student ends` with four fields, an array of four instances
  (`student <'Ali     ', , 91, 'A'>` - an empty value keeps the field's default),
* field access in every MASM / TASM form: `[si].mark`, `lea dx, [si].sname`, `(student ptr [si]).grade`,
  `student.sname` (the field offset) and `size student` (the size of one element),
* conditional assembly: `IF LANGUAGE EQ 1` / `ELSE` / `ENDIF` around data, `IFDEF SHOW_GRADES` with a nested
  `IF`, and `IFB <text>` inside a macro.

**Try it:** open `project.radproj` (File > Open Project) and press F5. Then set `SHOW_GRADES equ 0` or
`LANGUAGE = 2` and run it again. In the 8086 Emulator dock, **Export... > MZ .EXE** writes `main.exe` next to
the source: copy it into DOSBox (`mount c <folder>`, `c:`, `main`) and it prints the same lines.

**Expected result:**

```
Students of the 8086 course
Ali     91 A
Mona    78 C
Omar    85 B
Sara    96 A
Average mark: 87
Best student: Sara
```

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086Structs/main.asm`. The automated checks are in
`samples/Tests/Assembly/Emu8086Tests/test_struc_cond_export.py`.
