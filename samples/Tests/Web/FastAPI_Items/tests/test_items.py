import os
import tempfile
import unittest

os.environ["ITEMS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class ItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cm = TestClient(app)
        cls.client = cls.cm.__enter__()          # runs the lifespan (tables + demo items)

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def test_demo_items(self):
        names = [i["name"] for i in self.client.get("/items").json()]
        self.assertIn("Keyboard", names)

    def test_crud(self):
        r = self.client.post("/items", json={"name": "Cable", "price": 3.5})
        self.assertEqual(r.status_code, 201)
        item_id = r.json()["id"]
        self.assertEqual(self.client.get(f"/items/{item_id}").json()["name"], "Cable")
        r = self.client.put(f"/items/{item_id}", json={"price": 4.0, "in_stock": False})
        self.assertEqual(r.json()["price"], 4.0)
        self.assertFalse(r.json()["in_stock"])
        self.assertEqual(self.client.delete(f"/items/{item_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/items/{item_id}").status_code, 404)

    def test_validation_and_search(self):
        self.assertEqual(self.client.post("/items", json={"name": "", "price": -1}).status_code, 422)
        found = self.client.get("/items", params={"q": "wireless"}).json()
        self.assertEqual([i["name"] for i in found], ["Mouse"])

    def test_page(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Monitor", r.text)


if __name__ == "__main__":
    unittest.main()
