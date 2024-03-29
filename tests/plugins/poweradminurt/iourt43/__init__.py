import unittest

from mockito import when

from b3 import TEAM_UNKNOWN
from b3.clients import Cvar
from b3.config import CfgConfigParser
from b3.parsers.iourt43 import Iourt43Parser
from b3.plugins.admin import AdminPlugin
from tests import logging_disabled


class Iourt43TestCase(unittest.TestCase):
    """
    Test case that is suitable for testing Iourt43 parser specific features
    """

    @classmethod
    def setUpClass(cls):
        with logging_disabled():
            from b3.parsers.iourt43 import Iourt43Parser
            from tests.fake import FakeConsole

            Iourt43Parser.__bases__ = (FakeConsole,)

    def setUp(self):
        with logging_disabled():
            self.parser_conf = CfgConfigParser()
            self.parser_conf.loadFromString(
                """\
                [server]
                game_log:
            """
            )
            self.console = Iourt43Parser(self.parser_conf)
            self.console.startup()

            admin_plugin_conf_file = "@b3/conf/plugin_admin.ini"
            with logging_disabled():
                self.adminPlugin = AdminPlugin(self.console, admin_plugin_conf_file)
                self.adminPlugin.onLoadConfig()
                self.adminPlugin.onStartup()

            # make sure the admin plugin obtained by other plugins is our admin plugin
            when(self.console).getPlugin("admin").thenReturn(self.adminPlugin)
            when(self.console).queryClientFrozenSandAccount(...).thenReturn({})

            # prepare a few players
            from tests.fake import FakeClient

            self.joe = FakeClient(
                self.console,
                name="Joe",
                exactName="Joe",
                guid="zaerezarezar",
                groupBits=1,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )
            self.simon = FakeClient(
                self.console,
                name="Simon",
                exactName="Simon",
                guid="qsdfdsqfdsqf",
                groupBits=0,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )
            self.reg = FakeClient(
                self.console,
                name="Reg",
                exactName="Reg",
                guid="qsdfdsqfdsqf33",
                groupBits=4,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )
            self.moderator = FakeClient(
                self.console,
                name="Moderator",
                exactName="Moderator",
                guid="sdf455ezr",
                groupBits=8,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )
            self.admin = FakeClient(
                self.console,
                name="Level-40-Admin",
                exactName="Level-40-Admin",
                guid="875sasda",
                groupBits=16,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )
            self.superadmin = FakeClient(
                self.console,
                name="God",
                exactName="God",
                guid="f4qfer654r",
                groupBits=128,
                team=TEAM_UNKNOWN,
                teamId=0,
                squad=0,
            )

    def tearDown(self):
        self.console.shutdown()

    def init_default_cvar(self):
        when(self.console).getCvar("timelimit").thenReturn(Cvar("timelimit", value=20))
        when(self.console).getCvar("g_maxGameClients").thenReturn(
            Cvar("g_maxGameClients", value=16)
        )
        when(self.console).getCvar("sv_maxclients").thenReturn(
            Cvar("sv_maxclients", value=16)
        )
        when(self.console).getCvar("sv_privateClients").thenReturn(
            Cvar("sv_privateClients", value=0)
        )
        when(self.console).getCvar("g_allowvote").thenReturn(
            Cvar("g_allowvote", value=0)
        )
        when(self.console).getCvar("g_gear").thenReturn(Cvar("g_gear", value=""))
