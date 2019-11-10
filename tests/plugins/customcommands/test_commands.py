from mock import patch, call

from b3.config import CfgConfigParser
from b3.plugins.customcommands import CustomcommandsPlugin
from tests import logging_disabled
from tests.plugins.customcommands import CustomcommandsTestCase


class Test_commands(CustomcommandsTestCase):

    def setUp(self):
        CustomcommandsTestCase.setUp(self)
        self.conf = CfgConfigParser()
        self.p = CustomcommandsPlugin(self.console, self.conf)
        with logging_disabled():
            from b3.fake import FakeClient
        self.guest = FakeClient(console=self.console, name="Guest", guid="GuestGUID", pbid="GuestPBID", group_bits=0)
        self.user = FakeClient(console=self.console, name="User", guid="UserGUID", pbid="UserPBID", group_bits=1)
        self.regular = FakeClient(console=self.console, name="Regular", guid="RegularGUID", pbid="RegularPBID",
                                  group_bits=2)
        self.mod = FakeClient(console=self.console, name="Moderator", guid="ModeratorGUID", pbid="ModeratorPBID",
                              group_bits=8)
        self.admin = FakeClient(console=self.console, name="Admin", guid="AdminGUID", pbid="AdminPBID", group_bits=16)
        self.fulladmin = FakeClient(console=self.console, name="FullAdmin", guid="FullAdminGUID", pbid="FullAdminPBID",
                                    group_bits=32)
        self.senioradmin = FakeClient(console=self.console, name="SeniorAdmin", guid="SeniorAdminGUID",
                                      pbid="SeniorAdminPBID", group_bits=64)
        self.superadmin = FakeClient(console=self.console, name="SuperAdmin", guid="SuperAdminGUID",
                                     pbid="SuperAdminPBID", group_bits=128)

    def test_guest(self):
        # GIVEN
        self.conf.loadFromString("""
[guest commands]
# define in this section commands that will be available to all players
f00 = f00 rcon command
        """)
        # WHEN
        self.p.onLoadConfig()
        self.p.onStartup()
        # THEN
        self.assertIn("f00", self.p._adminPlugin._commands)
        # WHEN
        self.guest.connects(cid="guestCID")
        with patch.object(self.console, "write") as write_mock:
            self.guest.says("!f00")
        # THEN
        self.assertListEqual([call("f00 rcon command")], write_mock.mock_calls)
        self.assertListEqual([], self.guest.message_history)

    def test_user(self):
        # GIVEN
        self.console.getPlugin('admin')._warn_command_abusers = True
        self.conf.loadFromString("""
[user commands]
# define in this section commands that will be available to all players
f00 = f00 rcon command
        """)
        self.p.onLoadConfig()
        self.p.onStartup()
        # WHEN
        self.guest.connects(cid="guestCID")
        with patch.object(self.console, "write") as write_mock:
            self.guest.says("!f00")
        # THEN
        self.assertEqual(1, len(self.guest.message_history))
        self.assertIn(self.guest.message_history[0], [
            'You do not have sufficient access to use !f00',
            'You need to be in group User to use !f00'
        ])
        self.assertListEqual([], write_mock.mock_calls)
