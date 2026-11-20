"""Creates the People table on the IDE's local PostgreSQL server (Databases > Local Servers > Start local
PostgreSQL first, or this script starts it): python setup_db.py   (run with the IDE's .venv Python)."""
import os
import sys
from pathlib import Path

# the IDE folder: above this sample (samples/Tests/DataBinding/<this folder>/), else RADIDE_HOME
IDE = next((p for p in Path(__file__).resolve().parents if (p / "radide" / "__init__.py").is_file()),
           Path(os.environ.get("RADIDE_HOME", ".")))
sys.path.insert(0, str(IDE))
from radide.web_site.databases import open_database  # noqa: E402
from radide.web_site.dbservers import servers  # noqa: E402

SQL = "DROP TABLE IF EXISTS people;\nCREATE TABLE people(id SERIAL PRIMARY KEY, name VARCHAR(80) NOT NULL, city VARCHAR(60), age INT,\n                    score NUMERIC(6,2), active BOOLEAN DEFAULT TRUE);\nINSERT INTO people(name, city, age, score) VALUES ('Amira', 'Cairo', 29, 88.5), ('Omar', 'Giza', 34, 70),\n ('Lina', 'Aswan', 22, 95.25), ('Youssef', 'Luxor', 41, 61);"

srv = servers()["postgresql"]
if not srv.available:
    sys.exit("PostgreSQL is not installed (Databases > Local Servers)")
if not srv.is_running():
    print("starting", srv.title, "...")
    srv.start()
db = open_database(srv.connection_info("LocalDb"), None, srv.password())
for r in db.execute(SQL):
    if r.error:
        print("error:", r.error)
db.close()
print("People table ready on", srv.status())
