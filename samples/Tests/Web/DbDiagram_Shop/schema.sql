-- Shop database for the Database Diagram test (SQLite).
CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE);
CREATE TABLE categories (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL DEFAULT 0, category_id INTEGER);
CREATE INDEX ix_products_name ON products(name);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), created TEXT);
CREATE TABLE order_items (order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                          product_id INTEGER REFERENCES products(id), qty INTEGER,
                          PRIMARY KEY (order_id, product_id));
INSERT INTO customers(name, email) VALUES ('Ali', 'ali@example.com'), ('Mona', 'mona@example.com');
INSERT INTO categories VALUES (1, 'Books'), (2, 'Games');
INSERT INTO products VALUES (1, 'Novel', 10, 1), (2, 'Chess', 25, 2), (3, 'Pen', 1, NULL);
INSERT INTO orders VALUES (1, 1, '2026-01-01');
INSERT INTO order_items VALUES (1, 1, 2), (1, 2, 1);
