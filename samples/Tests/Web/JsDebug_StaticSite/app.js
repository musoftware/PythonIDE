// Breakpoints here pause the IDE's Preview (client-side JavaScript debugging).
function add(a, b) {
  const sum = a + b;
  return sum;
}

function onAddClick() {
  const a = Number(document.getElementById("a").value);
  const b = Number(document.getElementById("b").value);
  const total = add(a, b);
  document.getElementById("result").textContent = String(total);
}

const startedAt = new Date().toISOString();
document.getElementById("add").addEventListener("click", onAddClick);
console.log("page loaded at", startedAt);
