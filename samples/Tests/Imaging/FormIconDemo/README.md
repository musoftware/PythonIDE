# FormIconDemo - Icon Editor + project Resources (python-tk)

Made by the Icon / Image Editor test (round 7). It shows:

- `Resources/AppIcon.ico` - an icon **drawn pixel by pixel in the IDE's Icon Editor** (32x32 smiley with a
  half-transparent red blush), then *Generate All Sizes*: one file with 16, 24, 32, 48, 64 and 256 px images.
- **Form1.Icon** = `Resources/AppIcon.ico` (Tools > Image Editor > *Set as Form Icon*): the generated
  `Form1_designer.py` calls `self.root.iconbitmap(...)`, so the running window shows it in its title bar.
- **Application icon** (Tools > Image Editor > *Set as Application Icon*): `project.radproj` `"icon"` and
  `publish.json` `"icon"` - Build > Publish / the installer use it for the .exe and shortcuts.
- **Project resources** (`Resources/resources.json`, Project > Resources): a string `Greeting`, the image `Logo`
  and the icon `AppIcon`. The IDE generates `resources.py` (like VB's `My.Resources`):
  `Form1_Load` shows `R.strings.Greeting`; `picLogo.Image` was picked in the *Select Resource* dialog.

## How to try it

1. File > Open Project > this folder. Press **F5**: the window has the smiley in its title bar and task bar,
   the picture box shows the logo and the label says "Hello from the resources!".
2. Double-click *Resources > AppIcon.ico* in Solution Explorer (or Project > Resources > Icons > double-click):
   the Icon Editor opens. Pick the 16x16 image type on the right, draw with the Pencil (left button = primary
   colour, right button = secondary colour, Alpha slider for transparency), Ctrl+S, F5 again.
3. In the Form designer select the form, click the `...` of the **Icon** property (or `Image` of picLogo): the
   *Select Resource* dialog lists the project pictures; *Import...* adds a file, *New Icon...* draws a new one.
4. Project > Resources: add strings (`R.strings.Name`), images (`R.images.Name`, `R.photo("Name")` for Tk,
   `R.pixmap("Name")` for Qt) and files (`R.read_text("Name")`). Save regenerates `resources.py`.
