# DbDiagram_Shop

**Database Diagram** (Databases workspace): tables as boxes, foreign keys as lines, auto layout, new tables
and relationships drawn visually and applied as SQL DDL.

**Try it:**
1. Open the project. Databases > New SQLite Database... `data/shop.sqlite`.
2. New Query, paste `schema.sql`, Execute (5 tables, 3 foreign keys).
3. Right-click the connection > **Database Diagram** (or the *Diagram* button). Drag tables; *Auto Layout*
   puts parents left of their children; positions are saved in `.radide/db-diagrams.json`.
4. Click **New Relationship**, drag from `products.category_id` onto `categories.id`, choose *SET NULL*, OK:
   the SQL is shown first (SQLite rebuilds the table inside a transaction, data and indexes kept).
5. **New Table...** - columns grid with types / PK / not null; right-click a table for Add Column, Show CREATE
   SQL, Delete. *Export Image* saves PNG or SVG.
