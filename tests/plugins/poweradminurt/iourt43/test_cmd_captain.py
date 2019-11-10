from mock import call, Mock

from b3 import TEAM_BLUE
from b3 import TEAM_RED
from b3 import TEAM_SPEC
from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_captain(Iourt43TestCase):
    def setUp(self):
        super(Test_cmd_captain, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString("""
[commands]
pacaptain-captain: 40   ; set the the given client as the captain for its team
        """)
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()
        self.console.say = Mock()
        self.console.write = Mock()
        self.admin.connects("2")
        self.moderator.connects("3")

    def test_match_mode_deactivated(self):
        self.p._matchmode = False
        self.admin.message_history = []
        self.admin.says("!captain")
        self.assertListEqual(["!pacaptain command is available only in match mode"], self.admin.message_history)

    def test_client_spectator(self):
        self.p._matchmode = True
        self.admin.message_history = []
        self.admin.team = TEAM_SPEC
        self.admin.says("!captain")
        self.assertListEqual(["Level-40-Admin is a spectator! - Can't set captain status"], self.admin.message_history)

    def test_client_with_no_parameters(self):
        self.p._matchmode = True
        self.admin.message_history = []
        self.admin.team = TEAM_RED
        self.admin.says("!captain")
        self.console.write.assert_has_calls([call('forcecaptain %s' % self.admin.cid)])

    def test_client_with_parameters(self):
        self.p._matchmode = True
        self.admin.message_history = []
        self.admin.team = TEAM_RED
        self.moderator.message_history = []
        self.moderator.team = TEAM_BLUE
        self.admin.says("!captain 3")
        self.console.write.assert_has_calls([call('forcecaptain %s' % self.moderator.cid)])
        self.assertListEqual(["You were set as captain for the BLUE team by the Admin"], self.moderator.message_history)
