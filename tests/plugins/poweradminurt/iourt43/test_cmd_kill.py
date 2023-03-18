from unittest.mock import call, Mock

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_kill(Iourt43TestCase):
    def setUp(self):
        super(Test_cmd_kill, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
pakill-kill: 20
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def tearDown(self):
        super(Test_cmd_kill, self).tearDown()

    def test_no_argument(self):
        self.moderator.message_history = []
        self.moderator.says("!kill")
        self.assertEqual(
            ["invalid data, try !help pakill"], self.moderator.message_history
        )
        self.console.write.assert_has_calls([])

    def test_unknown_player(self):
        self.moderator.message_history = []
        self.moderator.says("!kill f00")
        self.assertEqual(
            ["No players found matching f00"], self.moderator.message_history
        )
        self.console.write.assert_has_calls([])

    def test_joe(self):
        self.joe.connects("3")
        self.moderator.message_history = []
        self.moderator.says("!kill joe")
        self.assertEqual([], self.moderator.message_history)
        self.assertEqual([], self.joe.message_history)
        self.console.write.assert_has_calls([call("smite 3")])
