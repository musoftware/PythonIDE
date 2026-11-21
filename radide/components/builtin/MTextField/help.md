# MTextField

Material outlined text field with a hint.

**Kind:** visual control. **Toolbox:** Mobile. **New name:** TextField1, TextField2 ...

**Default size:** 300 x 56 dp.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Hint | str | Enter text | Label shown while the field is empty. |
| Password | bool | false | Hide the characters. |

## Events

Double-clicking the control in the designer writes the handler of **Changed**.

- **Changed** - The value changed (Switch, Slider, TextField, BottomNav / TabBar index).
- **Submitted** - The user pressed Done / Enter on the keyboard.

See docs/COMPONENTS.md for how component packages work.
