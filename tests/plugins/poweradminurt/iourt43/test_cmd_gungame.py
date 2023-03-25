from unittest.mock import Mock, call

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_gungame(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
pagungame-gungame: 20           ; change game type to Gun Game
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def test_nominal(self):
        self.moderator.message_history = []
        self.moderator.says("!gungame")
        self.console.write.assert_has_calls([call('set g_gametype "11"')])
        self.assertEqual(
            ["game type changed to Gun Game"], self.moderator.message_history
        )
