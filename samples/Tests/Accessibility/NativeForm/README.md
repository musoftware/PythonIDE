# NativeForm (accessibility test program)

A C (GUI Bridge) form built by `samples/Tests/Accessibility/test_native_a11y.py` into a native radforms exe:
labels with access keys (`&Name:`), a text box, a check box, a list named by code (`AccessibleName`), RAD Modern
controls (RmButton, RmToggle, RmSlider, RmProgress, RmTextBox) and controls listed out of tab order on purpose
(the tab order must follow `TabIndex`). The test drives it with the keyboard and reads it with UI Automation.
