from unittest.mock import Mock, patch

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_ident(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
paident-id: 20

[special]
paident_full_level: 40
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.parser_conf.add_section("b3")
        self.parser_conf.set("b3", "time_zone", "UTC")
        self.parser_conf.set("b3", "time_format", "%I:%M%p %Z %m/%d/%y")
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")
        self.moderator.message_history = []

    def test_no_parameter(self):
        # WHEN
        self.moderator.says("!id")
        # THEN
        self.assertListEqual(["Your id is @2"], self.moderator.message_history)

    def test_junk(self):
        # WHEN
        self.moderator.says("!id qsdfsqdq sqfd qf")
        # THEN
        self.assertListEqual(
            ["No players found matching qsdfsqdq"], self.moderator.message_history
        )

    def test_nominal_under_full_level(self):
        # GIVEN
        self.joe.pbid = "joe_pbid"
        self.joe.connects("3")
        # WHEN
        with patch("time.time", return_value=0.0):
            self.moderator.says("!id joe")
        # THEN
        self.assertListEqual(
            ["12:00AM UTC 01/01/70 @3 Joe"], self.moderator.message_history
        )

    def test_nominal_above_full_level(self):
        # GIVEN
        self.joe.pbid = "joe_pbid"
        self.joe.connects("3")
        self.joe.timeAdd = 90 * 60.0
        self.superadmin.connects("1")
        # WHEN
        with patch("time.time", return_value=180 * 60.0):
            self.superadmin.says("!id joe")
        # THEN
        self.assertListEqual(
            ["03:00AM UTC 01/01/70 @3 Joe  [joe_pbid] since 01:30AM UTC 01/01/70"],
            self.superadmin.message_history,
        )
