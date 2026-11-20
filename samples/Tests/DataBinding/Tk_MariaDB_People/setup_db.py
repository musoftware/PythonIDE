"""Creates the People table on the IDE's local MariaDB server (Databases > Local Servers > Start local
MariaDB first, or this script starts it): python setup_db.py   (run with the IDE's .venv Python)."""
import os
import sys
from pathlib import Path

# the IDE folder: above this sample (samples/Tests/DataBinding/<this folder>/), else RADIDE_HOME
IDE = next((p for p in Path(__file__).resolve().parents if (p / "radide" / "__init__.py").is_file()),
           Path(os.environ.get("RADIDE_HOME", ".")))
sys.path.insert(0, str(IDE))
from radide.web_site.databases import open_database  # noqa: E402
from radide.web_site.dbservers import servers  # noqa: E402

SQL = "DROP TABLE IF EXISTS People;\nCREATE TABLE People(Id INT AUTO_INCREMENT PRIMARY KEY, Name VARCHAR(80) NOT NULL, City VARCHAR(60),\n                    Age INT, Score DECIMAL(6,2), Active TINYINT(1) DEFAULT 1);\nINSERT INTO People(Name, City, Age, Score) VALUES ('Amira', 'Cairo', 29, 88.5), ('Omar', 'Giza', 34, 70),\n ('Lina', 'Aswan', 22, 95.25), ('Youssef', 'Luxor', 41, 61);"

srv = servers()["mysql"]
if not srv.available:
    sys.exit("MariaDB is not installed (Databases > Local Servers)")
if not srv.is_running():
    print("starting", srv.title, "...")
    srv.start()
db = open_database(srv.connection_info("LocalDb"), None, srv.password())
for r in db.execute(SQL):
    if r.error:
        print("error:", r.error)
db.close()
print("People table ready on", srv.status())
