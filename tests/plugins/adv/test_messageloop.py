import unittest

from b3.plugins.adv import MessageLoop


class Test_MessageLoop(unittest.TestCase):

    def test_empty(self):
        ml = MessageLoop()
        self.assertEqual([], ml.items)
        self.assertEqual(None, ml.getnext())

    def test_one_element(self):
        ml = MessageLoop()
        ml.items = ['f00']
        self.assertEqual('f00', ml.getnext())
        self.assertEqual('f00', ml.getnext())

    def test_three_elements(self):
        ml = MessageLoop()
        ml.items = ['f001', 'f002', 'f003']
        self.assertEqual('f001', ml.getnext())
        self.assertEqual('f002', ml.getnext())
        self.assertEqual('f003', ml.getnext())
        self.assertEqual('f001', ml.getnext())
        self.assertEqual('f002', ml.getnext())
        self.assertEqual('f003', ml.getnext())

    def test_put(self):
        ml = MessageLoop()
        self.assertEqual([], ml.items)
        ml.put("bar")
        self.assertEqual(["bar"], ml.items)

    def test_getitem(self):
        ml = MessageLoop()
        ml.items = ['f00']
        self.assertEqual("f00", ml.getitem(0))
        self.assertEqual(None, ml.getitem(1))

    def test_remove(self):
        ml = MessageLoop()
        ml.items = ['f00', 'bar']
        self.assertEqual("f00", ml.getitem(0))
        ml.remove(0)
        self.assertEqual(['bar'], ml.items)
        self.assertEqual("bar", ml.getitem(0))

    def test_clear(self):
        ml = MessageLoop()
        ml.items = ['f00', 'bar']
        ml.clear()
        self.assertEqual([], ml.items)

    def test_truthiness(self):
        ml = MessageLoop()
        self.assertFalse(ml)
        ml.put("an item")
        self.assertTrue(ml)
        ml.clear()
        self.assertFalse(ml)
