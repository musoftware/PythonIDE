import unittest

from app import create_app


class TodoTests(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.app = create_app("config.TestingConfig")
        self.app.config["DATABASE"] = self.path
        self.client = self.app.test_client()

    def tearDown(self):
        import os
        os.remove(self.path)

    def test_add_toggle_delete(self):
        r = self.client.post("/add", data={"title": "Buy milk"}, follow_redirects=True)
        self.assertIn(b"Buy milk", r.data)
        todos = self.client.get("/api/todos").get_json()
        self.assertEqual(len(todos), 1)
        tid = todos[0]["id"]
        self.client.post(f"/{tid}/toggle")
        self.assertTrue(self.client.get("/api/todos").get_json()[0]["done"])
        self.client.post(f"/{tid}/delete")
        self.assertEqual(self.client.get("/api/todos").get_json(), [])

    def test_api(self):
        r = self.client.post("/api/todos", json={"title": "API todo"})
        self.assertEqual(r.status_code, 201)
        tid = r.get_json()["id"]
        r = self.client.patch(f"/api/todos/{tid}", json={"done": True})
        self.assertTrue(r.get_json()["done"])
        self.assertEqual(self.client.post("/api/todos", json={}).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/todos/{tid}").status_code, 204)

    def test_filter(self):
        self.client.post("/add", data={"title": "A"})
        self.client.post("/add", data={"title": "B"})
        tid = self.client.get("/api/todos").get_json()[0]["id"]
        self.client.post(f"/{tid}/toggle")
        page = self.client.get("/?show=done").data
        self.assertIn(b">A<", page)
        self.assertNotIn(b">B<", page)


if __name__ == "__main__":
    unittest.main()
