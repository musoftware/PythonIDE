import unittest

from report import summary, total_line


class ReportTests(unittest.TestCase):
    def test_total_line(self):
        print("checking total_line")
        self.assertEqual(total_line(1, 2), "1 + 2 = 3")

    def test_summary(self):
        self.assertEqual(summary([1, 2]), "average 1.5")
