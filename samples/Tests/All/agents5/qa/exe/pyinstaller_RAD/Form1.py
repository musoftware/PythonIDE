from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from tkinter import messagebox

# variables of the original program
count = 0



class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        pass

    def Button1_Click(self):
        self.greet()

    def Button2_Click(self):
        self.clear_log()



    # ---- code moved from the original program ----

    def greet(self):
        global count
        name = self.entry.get().strip()
        if not name:
            messagebox.showinfo('Hello', 'Please type a name')
            return None
        if self.CheckBox1_var.get():
            name = name.upper()
        count += 1
        self.result.config(text=f'Hello, {name}! ({count})')
        self.log.insert('end', name)

    def clear_log(self):
        self.log.delete(0, 'end')


if __name__ == "__main__":
    Form1().show()
