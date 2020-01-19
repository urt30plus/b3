import time
from unittest.mock import patch, call, Mock

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests import InstantThread
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class mixin_cmd_nuke:

    def setUp(self):
        super(mixin_cmd_nuke, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString("""
[commands]
panuke-nuke: 20
        """)
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.sleep_patcher = patch.object(time, 'sleep')
        self.sleep_patcher.start()

        self.console.say = Mock()
        self.console.saybig = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def tearDown(self):
        super(mixin_cmd_nuke, self).tearDown()
        self.sleep_patcher.stop()

    def test_no_argument(self):
        self.moderator.message_history = []
        self.moderator.says("!nuke")
        self.assertEqual(['Invalid data, try !help panuke'], self.moderator.message_history)
        self.console.write.assert_has_calls([])

    def test_unknown_player(self):
        self.moderator.message_history = []
        self.moderator.says("!nuke f00")
        self.assertEqual(['No players found matching f00'], self.moderator.message_history)
        self.console.write.assert_has_calls([])

    def test_joe(self):
        self.joe.connects('3')
        self.moderator.message_history = []
        self.moderator.says("!nuke joe")
        self.assertEqual([], self.moderator.message_history)
        self.assertEqual([], self.joe.message_history)
        self.console.write.assert_has_calls([call('nuke 3')])

    @patch('threading.Thread', new_callable=lambda: InstantThread)
    def test_joe_multi(self, instant_thread):
        self.joe.connects('3')
        self.moderator.message_history = []
        self.moderator.says("!nuke joe 3")
        self.assertEqual([], self.moderator.message_history)
        self.assertEqual([], self.joe.message_history)
        self.console.write.assert_has_calls([call('nuke 3'), call('nuke 3'), call('nuke 3')])


class Test_cmd_nuke_43(mixin_cmd_nuke, Iourt43TestCase):
    """
    call the mixin_cmd_nuke test using the Iourt43TestCase parent class
    """
