from unittest.mock import Mock, call

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_jump(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
pajump-jump: 20           ; change game type to Jump
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
        self.moderator.says("!jump")
        self.console.write.assert_has_calls([call('set g_gametype "9"')])
        self.assertEqual(["game type changed to Jump"], self.moderator.message_history)
