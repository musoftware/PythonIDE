# Kivy: Column / Row / Card / GroupBox / Stack containers

`Project/` is a Kivy phone screen whose controls sit in containers: a Column (a Label, a Button and a nested Row
with two buttons), a Row, a Card, a GroupBox and a Stack.

KV wants every property of a widget before its child widgets. The Kivy generator
(`radide/mobile/codegen_kivy.py`) used to write a container's children first and its size / position lines
after them, which Kivy's parser rejects ("Invalid data after declaration"); now the children come after the
container's own properties (`KivyFormGen.widget_head()` + `tail()`).

`check_kivy_containers.py` rebuilds the project, checks the KV order statically, loads the KV with
`kivy.lang.Builder` and runs the app (RADKIVY_EXEC): every control exists, children are inside their container,
the Column lays out top-down, the Row side by side, and a handler of a button inside the Column runs.

```bat
python samples\Tests\Mobile\Kivy_Containers\check_kivy_containers.py
cd samples\Tests\Mobile\Kivy_Containers\Project && python Form1.py
```
