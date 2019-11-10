import unittest

from b3.update import B3version


class TestB3Version(unittest.TestCase):
    def test_no_exception(self):
        B3version("1.4")
        B3version("1.4.2")
        B3version("0.7dev")
        B3version("0.7dev0")
        B3version("0.7dev4")
        B3version("1.8a")
        B3version("1.8a0")
        B3version("1.8a1")
        B3version("1.8a45")
        B3version("1.8b")
        B3version("1.8b0")
        B3version("1.8b78")
        B3version("0.7.2dev")
        B3version("0.7.2dev0")
        B3version("0.7.2dev4")
        B3version("1.8.2a")
        B3version("1.8.2a0")
        B3version("1.8.2a1")
        B3version("1.8.2a45")
        B3version("1.8.2b")
        B3version("1.8.2b0")
        B3version("1.8.2b78")
        B3version("1.9.0dev7.daily21-20121004")

    def test_exception(self):
        for version in ("1", "0", "24", '1.x', '1.5.2.1', '1.4alpha', '1.5.4beta', '1.6d'):
            try:
                B3version(version)
                self.fail("should have raised a ValueError for version '%s'" % version)
            except ValueError:
                pass

    def test_equals(self):
        self.assertEqual(B3version("1.1.0"), B3version('1.1'))
        self.assertEqual(B3version("1.1dev"), B3version('1.1dev0'))
        self.assertEqual(B3version("1.1.0dev"), B3version('1.1.0dev0'))
        self.assertEqual(B3version("1.1.0dev"), B3version('1.1dev0'))
        self.assertEqual(B3version("1.1a"), B3version('1.1a0'))
        self.assertEqual(B3version("1.1.0a"), B3version('1.1.0a0'))
        self.assertEqual(B3version("1.1b"), B3version('1.1b'))
        self.assertEqual(B3version("1.1.0b"), B3version('1.1.0b0'))
        self.assertEqual(B3version("1.1.0b"), B3version('1.1b0'))
        self.assertEqual(B3version("1.9.0dev7.daily21-20121004"), B3version("1.9dev7.daily21"))

    def test_greater(self):
        self.assertGreater(B3version('1.0'), B3version('1.0dev'))
        self.assertGreater(B3version('1.0'), B3version('1.0dev1'))
        self.assertGreater(B3version('1.0'), B3version('1.0.0dev'))
        self.assertGreater(B3version('1.0'), B3version('1.0.0dev2'))
        self.assertGreater(B3version('1.0'), B3version('1.0a'))
        self.assertGreater(B3version('1.0'), B3version('1.0a5'))
        self.assertGreater(B3version('1.0'), B3version('1.0b'))
        self.assertGreater(B3version('1.0'), B3version('1.0b5'))
        self.assertGreater(B3version('1.0'), B3version('0.5'))
        self.assertGreater(B3version('1.0'), B3version('0.5dev'))
        self.assertGreater(B3version('1.0'), B3version('0.5a'))
        self.assertGreater(B3version('1.0'), B3version('0.5b'))
        self.assertGreater(B3version("1.9.0dev7.daily21-20121004"), B3version("1.9dev7.daily19-20121001"))

    def test_less(self):
        self.assertLess(B3version('1.0'), B3version('1.0.1'))
        self.assertLess(B3version('1.0'), B3version('1.1'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.1dev6'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.1a'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.1a5'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.1b'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.1b5'))
        self.assertLess(B3version('2.5.1dev'), B3version('2.5.2'))
        self.assertLess(B3version('2.5.1dev5'), B3version('2.5.2'))
        self.assertLess(B3version('2.5.1a'), B3version('2.5.2'))
        self.assertLess(B3version('2.5.1a2'), B3version('2.5.2'))
        self.assertLess(B3version('2.5.1b'), B3version('2.5.2'))
        self.assertLess(B3version('2.5.1b4'), B3version('2.5.2'))
        self.assertLess(B3version("1.9.0dev7.daily5-20120904"), B3version("1.9dev7.daily19-20121001"))


if __name__ == '__main__':
    unittest.main()
