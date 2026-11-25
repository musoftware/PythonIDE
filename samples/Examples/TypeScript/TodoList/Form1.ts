// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Todo List - TypeScript with a RAD IDE form.
// Shows: a typed model (the TodoStore class in TodoModel.ts), JSON persistence (todos.json in the project
// folder, saved after every change), a ListBox showing the tasks, a ComboBox for the priority, a CheckBox
// filter, Enter in the TextBox adds a task (KeyPress), menus, and moving items up / down.

let store: TodoStore;
let shown: number[] = [];          // ListBox line -> index in store.items (the filter hides some tasks)

function Form1_Load(e: RadEvent): void {
    store = new TodoStore(require('path').join(__radfolder, 'todos.json'));
    store.load();
    set('cboPriority', 'Text', 'Normal');
    refresh();
}

// ------------------------------------------------------------------ adding
function cmdAdd_Click(e: RadEvent): void {
    const title = get('txtTask', 'Text').trim();
    if (!title) { msgbox('Type a task first.'); return; }
    store.add(title, get('cboPriority', 'Text') as Priority);
    set('txtTask', 'Text', '');
    refresh();
}

function txtTask_KeyPress(e: RadEvent): void {
    if (['13', 'Return'].includes(String(e.args).split(' ')[3])) cmdAdd_Click(e);       // Enter adds the task
}

// ------------------------------------------------------------------ editing
function cmdDone_Click(e: RadEvent): void { withSelected((i) => store.toggle(i)); }
function cmdDelete_Click(e: RadEvent): void { withSelected((i) => store.remove(i)); }
function cmdUp_Click(e: RadEvent): void { withSelected((i) => store.move(i, -1), -1); }
function cmdDown_Click(e: RadEvent): void { withSelected((i) => store.move(i, +1), +1); }
function lstTasks_DoubleClick(e: RadEvent): void { cmdDone_Click(e); }
function chkHideDone_CheckedChanged(e: RadEvent): void { refresh(); }

function mnuDone_Click(e: RadEvent): void { cmdDone_Click(e); }
function mnuDelete_Click(e: RadEvent): void { cmdDelete_Click(e); }

function mnuPurge_Click(e: RadEvent): void {
    const n = store.removeCompleted();
    refresh();
    msgbox(`${n} completed task(s) removed.`);
}

function mnuSave_Click(e: RadEvent): void { store.save(); msgbox('Saved to todos.json'); }
function mnuReload_Click(e: RadEvent): void { store.load(); refresh(); }
function mnuExit_Click(e: RadEvent): void { end(); }

// ------------------------------------------------------------------ helpers
/** Runs fn(index of the selected task) and keeps the selection on the same task. */
function withSelected(fn: (index: number) => void, shift: number = 0): void {
    const line = getNum('lstTasks', 'ListIndex');
    if (line < 0 || line >= shown.length) { msgbox('Select a task first.'); return; }
    fn(shown[line]);
    refresh();
    const next = Math.max(0, Math.min(shown.length - 1, line + shift));
    if (shown.length) set('lstTasks', 'ListIndex', next);
}

function refresh(): void {
    const hideDone = get('chkHideDone', 'Value') === '1';
    call('lstTasks', 'Clear');
    shown = [];
    store.items.forEach((t: Todo, i: number) => {
        if (hideDone && t.done) return;
        shown.push(i);
        call('lstTasks', 'AddItem', describe(t));
    });
    const s = store.summary();
    set('lblSummary', 'Caption', `${s.open} open, ${s.done} done, ${s.high} high priority`);
}
