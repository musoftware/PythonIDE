// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module TodoModel - the typed data of the Todo List: a Todo interface and a TodoStore class that keeps
// the tasks in a JSON file. No form code here, so the class could be unit-tested on its own.

type Priority = 'High' | 'Normal' | 'Low';

interface Todo {
    title: string;
    priority: Priority;
    done: boolean;
    created: string;         // ISO date
}

interface Summary { open: number; done: number; high: number; }

class TodoStore {
    items: Todo[] = [];

    constructor(private file: string) {}

    load(): void {
        const fs = require('fs');
        try {
            const data = JSON.parse(fs.readFileSync(this.file, 'utf8'));
            this.items = Array.isArray(data) ? data : [];
        } catch {
            this.items = [];
        }
    }

    save(): void {
        require('fs').writeFileSync(this.file, JSON.stringify(this.items, null, 2), 'utf8');
    }

    add(title: string, priority: Priority = 'Normal'): void {
        this.items.push({ title, priority: priority || 'Normal', done: false, created: new Date().toISOString() });
        this.save();
    }

    toggle(i: number): void { this.items[i].done = !this.items[i].done; this.save(); }

    remove(i: number): void { this.items.splice(i, 1); this.save(); }

    move(i: number, delta: number): void {
        const j = i + delta;
        if (j < 0 || j >= this.items.length) return;
        [this.items[i], this.items[j]] = [this.items[j], this.items[i]];
        this.save();
    }

    removeCompleted(): number {
        const before = this.items.length;
        this.items = this.items.filter((t) => !t.done);
        this.save();
        return before - this.items.length;
    }

    summary(): Summary {
        const done = this.items.filter((t) => t.done).length;
        return { open: this.items.length - done, done,
                 high: this.items.filter((t) => !t.done && t.priority === 'High').length };
    }
}

/** One ListBox line: "[x] (!) Buy milk". */
function describe(t: Todo): string {
    const mark = t.done ? '[x]' : '[ ]';
    const prio = t.priority === 'High' ? '(!) ' : t.priority === 'Low' ? '(low) ' : '';
    return `${mark} ${prio}${t.title}`;
}
