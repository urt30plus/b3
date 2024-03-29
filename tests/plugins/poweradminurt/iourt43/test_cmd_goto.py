from unittest.mock import Mock, call

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_goto(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
paskins-skins: 20       ; set the use of client skins <on/off>
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def test_missing_parameter(self):
        self.moderator.message_history = []
        self.moderator.says("!skins")
        self.assertListEqual(
            ["invalid or missing data, try !help paskins"],
            self.moderator.message_history,
        )

    def test_junk(self):
        self.moderator.message_history = []
        self.moderator.says("!skins qsdf")
        self.assertListEqual(
            ["invalid or missing data, try !help paskins"],
            self.moderator.message_history,
        )

    def test_on(self):
        self.moderator.says("!skins on")
        self.console.write.assert_has_calls([call('set g_skins "1"')])

    def test_off(self):
        self.moderator.says("!skins off")
        self.console.write.assert_has_calls([call('set g_skins "0"')])
