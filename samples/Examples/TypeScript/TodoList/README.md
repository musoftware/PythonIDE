# Todo List (TypeScript)

A task list with priorities, saved as JSON.

**What it shows**
- A typed model in `TodoModel.ts`: `type Priority`, `interface Todo`, and a `class TodoStore` (parameter property,
  load / save / add / toggle / move / removeCompleted) - the form only displays it.
- JSON persistence: `todos.json` in the project folder is written after every change and read on start.
- `ListBox` (`ListIndex`, `DoubleClick`), `ComboBox` priority, a `CheckBox` filter ("Hide completed tasks"),
  Enter in the text box adds the task (`KeyPress`), Move Up / Down, Edit and File menus.
- Arabic task titles are saved and shown like any other text.

**Run**: open the folder, **F5**, type a task and press Enter.
**Publish**: Build > Publish (GUI Bridge program, Python inside; Node.js needed on the PC).

---

# قائمة المهام (TypeScript)

قائمة مهام بأولويات تُحفظ بصيغة JSON.

**ماذا يوضح**
- نموذج بيانات بأنواع في `TodoModel.ts` (نوع للأولوية وواجهة للمهمة وفئة `TodoStore`)، والنموذج المرئي يعرضه فقط.
- الحفظ في `todos.json` بعد كل تغيير والقراءة عند البدء.
- قائمة `ListBox` وقائمة أولوية منسدلة وخانة اختيار لإخفاء المهام المنتهية، وزر Enter يضيف المهمة، والتحريك لأعلى ولأسفل.
- عناوين المهام بالعربية تُحفظ وتظهر بشكل طبيعي.

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج Node.js على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
