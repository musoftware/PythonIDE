import tkinter as tk
from tkinter import messagebox

count = 0


def greet():
    global count
    name = entry.get().strip()
    if not name:
        messagebox.showinfo("Hello", "Please type a name")
        return
    if upper.get():
        name = name.upper()
    count += 1
    result.config(text=f"Hello, {name}! ({count})")
    log.insert("end", name)


def clear_log():
    log.delete(0, "end")


root = tk.Tk()
root.title("Hello Tk")
root.geometry("360x260")
entry = tk.Entry(root)
entry.insert(0, "World")
entry.place(x=12, y=12, width=200, height=24)
tk.Button(root, text="Greet", command=greet).place(x=224, y=10, width=100, height=28)
upper = tk.BooleanVar()
tk.Checkbutton(root, text="Upper case", variable=upper).place(x=12, y=44)
result = tk.Label(root, text="Type a name", fg="navy")
result.place(x=12, y=80, width=312, height=28)
log = tk.Listbox(root)
log.place(x=12, y=116, width=312, height=100)
tk.Button(root, text="Clear", command=clear_log).place(x=12, y=222, width=80, height=26)
root.mainloop()
