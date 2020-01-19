from unittest.mock import call, Mock

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_funstuff(Iourt43TestCase):
    def setUp(self):
        super(Test_cmd_funstuff, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString("""
[commands]
pafunstuff-funstuff: 20 ; set the use of funstuff <on/off>
        """)
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def test_missing_parameter(self):
        self.moderator.message_history = []
        self.moderator.says("!funstuff")
        self.assertListEqual(["invalid or missing data, try !help pafunstuff"], self.moderator.message_history)

    def test_junk(self):
        self.moderator.message_history = []
        self.moderator.says("!funstuff qsdf")
        self.assertListEqual(["invalid or missing data, try !help pafunstuff"], self.moderator.message_history)

    def test_on(self):
        self.moderator.says("!funstuff on")
        self.console.write.assert_has_calls([call('set g_funstuff "1"')])

    def test_off(self):
        self.moderator.says("!funstuff off")
        self.console.write.assert_has_calls([call('set g_funstuff "0"')])
