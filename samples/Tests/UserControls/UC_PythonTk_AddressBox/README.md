# UC_PythonTk_AddressBox

**python-tk** - VB-style **user controls**: `AddressBox` (a user control with its own properties *Caption*
(maps to lblTitle.Text), *Street* (maps to txtStreet.Text), *Changes* and its own event *Changed*), reused
**twice** on `Form1` (HomeAddress, WorkAddress) and **nested** inside another user control `ContactCard`
(which raises its own *Edited* event when the inner AddressBox changes).

**What it tests:** one generated class per user control (`AddressBox_designer.py`, `ContactCard_designer.py`),
custom properties set on each instance, `self.RaiseEvent("Changed")` reaching the form's
`HomeAddress_Changed()`, events bubbling from a nested user control, properties read/written from code
(`self.WorkAddress.Street = self.HomeAddress.Street`).

**Try it:** open the folder, press F5 and type a street in *Home address* (the label at the right shows the
event), type in the *Postal address* of the card, click *Copy home -> work*. In the IDE: the Toolbox shows a
**"UC_PythonTk_AddressBox Components"** group with AddressBox / ContactCard; select an instance on Form1 to
see *Caption / Street / Changes* in the Properties window (category Custom) and *Changed* in the Events list;
open `AddressBox.form` and use right-click > *User Control Properties and Events...* to edit its interface.
Each user control can also be run alone (`python AddressBox.py`).

*Origin:* built by the user-controls agent's test script (generated with the IDE's own code generator, Python (Tkinter)).
