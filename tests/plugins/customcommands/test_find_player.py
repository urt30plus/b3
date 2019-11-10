from mock import patch

from b3.config import CfgConfigParser
from b3.plugins.customcommands import CustomcommandsPlugin
from tests import logging_disabled
from tests.plugins.customcommands import CustomcommandsTestCase

with logging_disabled():
    from b3.fake import FakeClient


class Test_find_player(CustomcommandsTestCase):
    def setUp(self):
        with logging_disabled():
            CustomcommandsTestCase.setUp(self)
            self.conf = CfgConfigParser()
            self.p = CustomcommandsPlugin(self.console, self.conf)
            self.guest = FakeClient(console=self.console, name="Guest", guid="GuestGUID", pbid="GuestPBID",
                                    group_bits=0)
            self.player1 = FakeClient(console=self.console, name="player1", guid="player1GUID", pbid="player1PBID",
                                      group_bits=1)
            self.player1.connects(cid="CID1")
            self.player2 = FakeClient(console=self.console, name="player2", guid="player2GUID", pbid="player2PBID",
                                      group_bits=1)
            self.player2.connects(cid="CID2")
            self.guest.connects(cid="guestCID")

    def init(self, conf_content):
        with logging_disabled():
            self.conf.loadFromString(conf_content)
            self.p.onLoadConfig()
            self.p.onStartup()

    def test_ARG_FIND_PLAYER_NAME_no_parameter(self):
        # GIVEN
        self.init("""
[guest commands]
f00 = f00 #<ARG:FIND_PLAYER:NAME>#
        """)

        # WHEN
        with patch.object(self.console, "write") as write_mock:
            self.guest.says("!f00")

        # THEN
        self.assertListEqual(['Error: missing parameter'], self.guest.message_history)
        self.assertListEqual([], write_mock.mock_calls)

    def test_ARG_FIND_PLAYER_NAME_no_match(self):
        # GIVEN
        self.init("""
[guest commands]
f00 = f00 #<ARG:FIND_PLAYER:NAME>#
        """)

        # WHEN
        with patch.object(self.console, "write") as write_mock:
            self.guest.says("!f00 bar")

        # THEN
        self.assertListEqual(['No players found matching bar'], self.guest.message_history)
        self.assertListEqual([], write_mock.mock_calls)

    def test_ARG_FIND_PLAYER_NAME_with_multiple_matches(self):
        # GIVEN
        self.init("""
[guest commands]
f00 = f00 #<ARG:FIND_PLAYER:NAME>#
        """)

        # WHEN
        with patch.object(self.console, "write") as write_mock:
            self.guest.says("!f00 player")

        # THEN
        self.assertListEqual(['Players matching player player1 [CID1], player2 [CID2]'], self.guest.message_history)
        self.assertListEqual([], write_mock.mock_calls)
