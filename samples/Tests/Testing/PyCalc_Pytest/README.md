# PyCalc_Pytest

Tests: **Test Explorer** with pytest and unittest, **code coverage** gutters, **Format Document / Format on
Save**, and the **refactoring** commands (F2 Rename across files, Ctrl+. quick actions, Extract Variable /
Method, Find All References) through the pylsp language server.

* `calc.py` - code under test; `report.py` uses `calc.add`; `tests/test_calc.py` (pytest: a failing test
  `test_grade_pass`, a parametrized test, a skipped test); `tests/test_report.py` (unittest class).
* `messy_format.py` - badly formatted on purpose.

**Try it**
1. Open the folder, **Test > Test Explorer**, **Run All**: 8 passed, 1 failed, 1 skipped. Double-click
   `test_grade_pass` - the editor opens at the test; the *Test Detail* tab shows the assert message.
2. **Test > Run All Tests with Coverage**, open `calc.py`: green bars = run by a test, red = never run
   (`never_tested`), amber = a branch not taken. The *Coverage* tab lists every file with its %.
3. Put a breakpoint in `tests/test_calc.py` (F9), select `test_add`, press the bug button (**Debug**).
4. Open `messy_format.py`, **Edit > Format Document** (Shift+Alt+F) - one Ctrl+Z undoes it all.
   **Edit > Format on Save** formats when you save.
5. In `calc.py` put the cursor on `add`, press **F2**, type a new name: the preview lists `calc.py`,
   `report.py` and `tests/test_calc.py`; Apply. **Shift+F12** lists all references.
6. Select `sum(values) / len(values)` and choose **Edit > Refactor > Extract Variable**, or press **Ctrl+.**
