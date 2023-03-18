from textwrap import dedent

from mockito import when

from b3 import TEAM_RED
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from b3.plugins.stats import StatsPlugin
from tests import B3TestCase, logging_disabled
from tests.fake import FakeClient


class StatPluginTestCase(B3TestCase):
    def setUp(self):
        B3TestCase.setUp(self)

        with logging_disabled():
            admin_conf = CfgConfigParser()
            admin_plugin = AdminPlugin(self.console, admin_conf)
            admin_plugin.onLoadConfig()
            admin_plugin.onStartup()
            when(self.console).getPlugin("admin").thenReturn(admin_plugin)

        conf = CfgConfigParser()
        conf.loadFromString(
            dedent(
                r"""
            [commands]
            mapstats-stats: 0
            testscore: 0
            topstats-top: 0
            topxp: 0

            [settings]
            startPoints: 100
            resetscore: no
            resetxp: no
            show_awards: no
            show_awards_xp: no
        """
            )
        )
        self.p = StatsPlugin(self.console, conf)
        self.p.onLoadConfig()
        self.p.onStartup()

        self.joe = FakeClient(
            self.console, name="Joe", guid="joeguid", groupBits=1, team=TEAM_RED
        )
        self.mike = FakeClient(
            self.console, name="Mike", guid="mikeguid", groupBits=1, team=TEAM_RED
        )
        self.joe.connects(1)
        self.mike.connects(2)
