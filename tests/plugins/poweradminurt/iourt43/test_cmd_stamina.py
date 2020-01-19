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
pastamina-stamina: 20   ; set the stamina behavior <default/regain/infinite>
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
        self.moderator.says("!stamina")
        self.assertListEqual(["invalid or missing data, try !help pastamina"], self.moderator.message_history)

    def test_junk(self):
        self.moderator.message_history = []
        self.moderator.says("!stamina qsdf")
        self.assertListEqual(["invalid or missing data, try !help pastamina"], self.moderator.message_history)

    def test_default(self):
        self.moderator.says("!stamina default")
        self.console.write.assert_has_calls([call('set g_stamina "0"')])

    def test_regain(self):
        self.moderator.says("!stamina regain")
        self.console.write.assert_has_calls([call('set g_stamina "1"')])

    def test_infinite(self):
        self.moderator.says("!stamina infinite")
        self.console.write.assert_has_calls([call('set g_stamina "2"')])
