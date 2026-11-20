from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """People lives on the IDE's local server; F5 from the IDE passes the password (RADIDE_DB_LOCALDB_PASSWORD)."""

    def btnReload_Click(self):
        self.People.Fill()


if __name__ == "__main__":
    Form1().show()
