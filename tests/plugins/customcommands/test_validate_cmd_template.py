from mock import Mock
from unittest import TestCase

from b3.config import CfgConfigParser
from b3.plugins.customcommands import CustomcommandsPlugin


class Test_validate_cmd_template(TestCase):

    def setUp(self):
        self.conf = CfgConfigParser()
        self.p = CustomcommandsPlugin(Mock(), self.conf)

    def test_nominal(self):
        try:
            self.p._validate_cmd_template("cookie")
        except (AssertionError, ValueError) as err:
            self.fail("expecting no error, got %r" % err)

    def test_None(self):
        self.assertRaises(AssertionError, self.p._validate_cmd_template, None)

    def test_blank(self):
        self.assertRaises(ValueError, self.p._validate_cmd_template, "  ")

    def test_ARG_placeholders(self):
        self.assertRaises(ValueError, self.p._validate_cmd_template, "tell <ARG:FIND_PLAYER:PID> <ARG:FIND_MAP> hi")
        self.p._validate_cmd_template("tell <ARG:FIND_PLAYER:PID> hi")
