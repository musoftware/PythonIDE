# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""python -m unittest discover -s tests  (FastAPI TestClient needs httpx: pip install httpx)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TASKS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

try:
    from fastapi.testclient import TestClient
    from app.main import app
except ImportError:          # httpx is not installed
    TestClient = None


@unittest.skipIf(TestClient is None, "pip install httpx to run the API tests")
class TaskApiTests(unittest.TestCase):
    def test_crud(self):
        c = TestClient(app)
        t = c.post("/api/tasks", json={"title": "Write README", "priority": "high"}).json()
        self.assertFalse(t["done"])
        self.assertTrue(c.patch(f"/api/tasks/{t['id']}", json={"done": True}).json()["done"])
        self.assertEqual(c.delete(f"/api/tasks/{t['id']}").status_code, 204)

    def test_validation(self):
        self.assertEqual(TestClient(app).post("/api/tasks", json={"title": "", "priority": "x"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
