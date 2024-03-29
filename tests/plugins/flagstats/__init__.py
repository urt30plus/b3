import unittest
from textwrap import dedent

from mockito import when

from b3 import TEAM_BLUE, TEAM_RED
from b3.clients import Cvar
from b3.config import CfgConfigParser, MainConfig
from b3.parsers.iourt43 import Iourt43Parser
from b3.plugins.admin import AdminPlugin
from b3.plugins.flagstats import FlagstatsPlugin
from tests import logging_disabled


class FlagstatsPluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with logging_disabled():
            from b3.parsers.iourt43 import Iourt43Parser
            from tests.fake import FakeConsole

            Iourt43Parser.__bases__ = (FakeConsole,)
            # Now parser inheritance hierarchy is :
            # Iourt43Parser -> abstractParser -> FakeConsole -> Parser

    def setUp(self):
        # create a Iourt43 parser
        parser_conf = CfgConfigParser()
        parser_conf.loadFromString(
            dedent(
                r"""
            [server]
            game_log:
        """
            )
        )

        self.parser_conf = MainConfig(parser_conf)
        self.console = Iourt43Parser(self.parser_conf)

        # initialize some fixed cvars which will be used by both the plugin and the iourt42 parser
        when(self.console).getCvar("auth").thenReturn(Cvar("auth", value="0"))
        when(self.console).getCvar("auth_owners").thenReturn(None)
        when(self.console).getCvar("fs_basepath").thenReturn(
            Cvar("fs_basepath", value="/fake/basepath")
        )
        when(self.console).getCvar("fs_homepath").thenReturn(
            Cvar("fs_homepath", value="/fake/homepath")
        )
        when(self.console).getCvar("fs_game").thenReturn(Cvar("fs_game", value="q3ut4"))
        when(self.console).getCvar("gamename").thenReturn(
            Cvar("gamename", value="q3urt43")
        )

        self.console.game.gameType = "ctf"

        # start the parser
        self.console.startup()

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, "@b3/conf/plugin_admin.ini")
            self.adminPlugin.onLoadConfig()
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin("admin").thenReturn(self.adminPlugin)

        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            dedent(
                r"""
            [commands]
            flagstats: 1
            topstats: 40

            [settings]
        """
            )
        )

        self.p = FlagstatsPlugin(self.console, self.conf)
        self.p.onLoadConfig()
        self.p.onStartup()

        with logging_disabled():
            from tests.fake import FakeClient

        # create some clients
        self.mike = FakeClient(
            console=self.console,
            name="Mike",
            guid="mikeguid",
            team=TEAM_BLUE,
            groupBits=1,
        )
        self.mark = FakeClient(
            console=self.console,
            name="Mark",
            guid="markguid",
            team=TEAM_BLUE,
            groupBits=1,
        )
        self.bill = FakeClient(
            console=self.console,
            name="Bill",
            guid="billguid",
            team=TEAM_RED,
            groupBits=1,
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mark.connects("3")

    def tearDown(self):
        self.console.shutdown()
        self.mike.disconnects()
        self.bill.disconnects()
        self.mark.disconnects()
