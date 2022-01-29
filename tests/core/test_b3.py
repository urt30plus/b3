import os

import b3
import b3.functions
import b3.parser
from tests import B3TestCase


class Test_getConfPath(B3TestCase):

    def test_get_b3_path(self):
        b3_path = b3.functions.getB3Path()
        self.assertTrue(os.path.exists(b3_path))

    def test_getConfPath(self):
        self.console.config.fileName = "/some/where/conf/b3.ini"
        self.assertEqual('/some/where/conf', b3.config.getConfPath())
        self.console.config.fileName = "./b3.ini"
        self.assertEqual('.', b3.config.getConfPath())

    def test_getConfPath_invalid(self):
        self.assertRaises(TypeError, b3.config.getConfPath, {"decode": False, "conf": self})


class Test_loading_parser(B3TestCase):

    def test_load_parser(self):
        parser_class = b3.functions.loadParser("iourt43")
        self.assertTrue(issubclass(parser_class, b3.parser.Parser))
