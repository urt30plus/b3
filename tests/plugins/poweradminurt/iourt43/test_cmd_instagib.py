from unittest.mock import call, Mock

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_instagib(Iourt43TestCase):
    def setUp(self):
        super(Test_cmd_instagib, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
painstagib-instagib: 20           ; change game mode to Instagib
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
        self.moderator.says("!instagib on")
        self.console.write.assert_has_calls([call('set g_instagib "1"')])

        self.moderator.says("!instagib off")
        self.console.write.assert_has_calls([call('set g_instagib "0"')])
