# CourseTests

Checks of the Arabic Assembly course (`radide/tutorials/assembly`, runner `radide/tutorials/asm_support.py`).

    python radide/tutorials/assembly/tools/check_lessons.py              # every block of the 16 lessons (NASM + gcc, 8086 emulator, quiz JSON, "جرّبه" projects)
    python samples/Tests/Assembly/CourseTests/test_course_forms.py       # the GUI Bridge forms of lesson 12, built and driven over the bridge protocol
    python tools/build_chm.py assembly --verify                          # docs/chm/RADIDE_ASSEMBLY_ar.chm
