from AddressBox_designer import AddressBoxDesigner, EventArgs  # noqa: F401


class AddressBox(AddressBoxDesigner):
    """User control: write its event handlers here.
    Raise its own events with self.RaiseEvent("EventName") - the form that hosts it
    gets <instance>_EventName(). Custom properties are declared in the designer
    (Project > User Control Properties and Events)."""

    def AddressBox_Load(self):
        pass

    def txtStreet_TextChanged(self, *_a):
        self.Changes += 1
        self.RaiseEvent("Changed")

    def cmbCity_SelectedIndexChanged(self, *_a):
        self.RaiseEvent("Changed")


if __name__ == "__main__":      # test the user control alone
    AddressBox().show()
