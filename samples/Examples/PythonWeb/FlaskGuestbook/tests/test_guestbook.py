# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Run with View > Flask > Run tests (python -m unittest discover -s tests)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402


class GuestbookTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        self.app = create_app()
        self.app.config.update(TESTING=True, DATABASE=self.db)
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db)

    def test_sign_and_list(self):
        r = self.client.post("/sign", data={"name": "Mona", "message": "Lovely site", "rating": "4"},
                             follow_redirects=True)
        self.assertIn(b"Lovely site", r.data)

    def test_validation(self):
        r = self.client.post("/sign", data={"name": "", "message": "x", "rating": "9"})
        self.assertIn(b"Please enter your name", r.data)

    def test_api(self):
        r = self.client.post("/api/entries", json={"name": "Api", "message": "via JSON"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get("/api/entries").get_json()[0]["name"], "Api")


if __name__ == "__main__":
    unittest.main()
