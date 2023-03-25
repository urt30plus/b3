from unittest.mock import Mock, call

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_skins(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
pagoto-goto: 20         ; set the goto <on/off>
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
        self.moderator.says("!goto")
        self.assertListEqual(
            ["invalid or missing data, try !help pagoto"],
            self.moderator.message_history,
        )

    def test_junk(self):
        self.moderator.message_history = []
        self.moderator.says("!goto qsdf")
        self.assertListEqual(
            ["invalid or missing data, try !help pagoto"],
            self.moderator.message_history,
        )

    def test_on(self):
        self.moderator.says("!goto on")
        self.console.write.assert_has_calls([call('set g_allowgoto "1"')])

    def test_off(self):
        self.moderator.says("!goto off")
        self.console.write.assert_has_calls([call('set g_allowgoto "0"')])
