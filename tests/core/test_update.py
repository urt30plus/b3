import unittest

from b3.update import B3version


class TestB3Version(unittest.TestCase):
    def test_no_exception(self):
        B3version("1.4")
        B3version("1.4.2")

    def test_exception(self):
        for version in ("1.x", "1.6d"):
            try:
                B3version(version)
                self.fail("should have raised a ValueError for version '%s'" % version)
            except ValueError:
                pass

    def test_equals(self):
        self.assertEqual(B3version("1.1.0"), B3version("1.1.0"))
        self.assertEqual(B3version("1.1.0"), B3version("1.1"))

    def test_greater(self):
        self.assertGreater(B3version("1.0"), B3version("0.5"))
        self.assertGreater(B3version("1.0.6"), B3version("1.0.5"))

    def test_less(self):
        self.assertLess(B3version("1.0"), B3version("1.0.1"))
        self.assertLess(B3version("1.0"), B3version("1.1"))


if __name__ == "__main__":
    unittest.main()
