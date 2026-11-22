// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// store.js - the shopping list shared by both screens (a plain module: File > Add Module).
// Items: { name, qty, bought }.  RadApp.data would work too; a module keeps the logic testable with Node.

export const store = { items: [], version: 0 };

export function addItem(name) {
  const clean = String(name || '').trim();
  if (!clean) return 'Type an item first';
  const found = store.items.find((i) => i.name.toLowerCase() === clean.toLowerCase());
  if (found) { found.qty += 1; store.version++; return `${found.name}: ${found.qty}`; }
  store.items.push({ name: clean, qty: 1, bought: false });
  store.version++;
  return '';
}

export function updateItem(index, changes) {
  Object.assign(store.items[index], changes);
  store.version++;
}

export function removeItem(index) {
  store.items.splice(index, 1);
  store.version++;
}

export function removeBought() {
  const before = store.items.length;
  store.items = store.items.filter((i) => !i.bought);
  store.version++;
  return before - store.items.length;
}

export function summary() {
  const left = store.items.filter((i) => !i.bought).length;
  if (!store.items.length) return 'Your list is empty.';
  return `${store.items.length} items - ${left} still to buy`;
}

// list rows for the MListView template icon|title|subtitle
export function rows(hideBought) {
  return store.items
    .map((it, index) => ({ it, index }))
    .filter(({ it }) => !hideBought || !it.bought)
    .map(({ it, index }) => ({ index, row: `${it.bought ? 'check_circle' : 'shopping_cart'}|${it.name}|x ${it.qty}` }));
}
