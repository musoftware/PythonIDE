import unittest

from wordstat import count_words


class CoreTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(count_words("a b a")["a"], 2)


if __name__ == "__main__":
    unittest.main()
