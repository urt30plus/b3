from textwrap import dedent

from b3.config import CfgConfigParser
from b3.plugins.stats import StatsPlugin
from tests import B3TestCase


class Test_config(B3TestCase):
    def test_empty(self):
        # GIVEN
        conf = CfgConfigParser()
        conf.loadFromString(
            dedent(
                r"""
        """
            )
        )
        self.p = StatsPlugin(self.console, conf)
        # WHEN
        self.p.onLoadConfig()
        # THEN
        self.assertEqual(0, self.p.mapstatslevel)
        self.assertEqual(0, self.p.testscorelevel)
        self.assertEqual(2, self.p.topstatslevel)
        self.assertEqual(2, self.p.topxplevel)
        self.assertEqual(100, self.p.startPoints)
        self.assertFalse(self.p.resetscore)
        self.assertFalse(self.p.resetxp)
        self.assertFalse(self.p.show_awards)
        self.assertFalse(self.p.show_awards_xp)

    def test_nominal(self):
        # GIVEN
        conf = CfgConfigParser()
        conf.loadFromString(
            dedent(
                r"""
            [commands]
            mapstats-stats: 2
            testscore: 2
            topstats-top: 20
            topxp: 20

            [settings]
            startPoints: 150
            resetscore: yes
            resetxp: yes
            show_awards: yes
            show_awards_xp: yes
        """
            )
        )
        self.p = StatsPlugin(self.console, conf)
        # WHEN
        self.p.onLoadConfig()
        # THEN
        self.assertEqual(2, self.p.mapstatslevel)
        self.assertEqual(2, self.p.testscorelevel)
        self.assertEqual(20, self.p.topstatslevel)
        self.assertEqual(20, self.p.topxplevel)
        self.assertEqual(150, self.p.startPoints)
        self.assertTrue(self.p.resetscore)
        self.assertTrue(self.p.resetxp)
        self.assertTrue(self.p.show_awards)
        self.assertTrue(self.p.show_awards_xp)
