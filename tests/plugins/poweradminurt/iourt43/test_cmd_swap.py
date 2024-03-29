from unittest.mock import Mock, call

from b3 import TEAM_BLUE, TEAM_RED
from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_swap(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
paswap-swap: 20
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()
        self.console.say = Mock()
        self.console.write = Mock()
        self.admin.connects("2")
        self.moderator.connects("3")

    def test_plugin_using_overridden_command_method(self):
        self.admin.team = TEAM_RED
        self.moderator.team = TEAM_BLUE
        self.admin.says("!swap 2 3")
        self.console.write.assert_has_calls(
            [call(f"swap {self.admin.cid} {self.moderator.cid}")]
        )
