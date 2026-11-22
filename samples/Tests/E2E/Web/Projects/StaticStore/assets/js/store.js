// RAD Store - renders the catalogue from data/products.json
'use strict';

async function loadProducts() {
    const res = await fetch('data/products.json');
    const items = await res.json();
    const rows = items.map(p => `<tr><td class="name">${p.name}</td><td>${p.price.toFixed(2)}</td></tr>`);
    document.querySelector('#products tbody').innerHTML = rows.join('');
    document.getElementById('total').textContent = `${items.length} products`;
}

document.addEventListener('DOMContentLoaded', loadProducts);
