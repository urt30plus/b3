from b3 import TEAM_BLUE, TEAM_FREE, TEAM_RED
from tests.plugins.stats import StatPluginTestCase


class Test_cmd_mapstats(StatPluginTestCase):
    def test_no_activity(self):
        # WHEN
        self.joe.says("!mapstats")
        # THEN
        self.assertListEqual(
            ["Stats [ Joe ] K 0 D 0 A 0 TK 0 Dmg 0 Skill 100.00 XP 0.0"],
            self.joe.message_history,
        )

    def test_tk(self):
        # GIVEN
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!mapstats")
        # THEN
        self.assertListEqual(
            ["Stats [ Joe ] K 0 D 0 A 0 TK 1 Dmg 0 Skill 87.50 XP 0.0"],
            self.joe.message_history,
        )
        # WHEN
        self.mike.says("!mapstats")
        # THEN
        self.assertListEqual(
            ["Stats [ Mike ] K 0 D 0 A 0 TK 0 Dmg 0 Skill 100.00 XP 0.0"],
            self.mike.message_history,
        )

    def test_kill(self):
        # GIVEN
        self.joe.team = TEAM_BLUE
        self.mike.team = TEAM_RED
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!mapstats")
        # THEN
        self.assertListEqual(
            ["Stats [ Joe ] K 1 D 0 A 0 TK 0 Dmg 100 Skill 112.50 XP 12.5"],
            self.joe.message_history,
        )
        # WHEN
        self.mike.says("!mapstats")
        # THEN
        self.assertListEqual(
            ["Stats [ Mike ] K 0 D 1 A 0 TK 0 Dmg 0 Skill 87.50 XP 0.0"],
            self.mike.message_history,
        )


class Test_cmd_testscore(StatPluginTestCase):
    def test_no_data(self):
        # WHEN
        self.joe.says("!testscore")
        # THEN
        self.assertListEqual(
            ["You must supply a player name to test"], self.joe.message_history
        )

    def test_self(self):
        # WHEN
        self.joe.says("!testscore joe")
        # THEN
        self.assertListEqual(
            ["You don't get points for killing yourself"], self.joe.message_history
        )

    def test_teammate(self):
        # GIVEN
        assert self.joe.team == self.mike.team
        # WHEN
        self.joe.says("!testscore mike")
        # THEN
        self.assertListEqual(
            ["You don't get points for killing a team mate"], self.joe.message_history
        )

    def test_no_team(self):
        # GIVEN
        self.joe.team = TEAM_FREE
        self.mike.team = TEAM_FREE
        assert self.joe.team == self.mike.team
        # WHEN
        self.joe.says("!testscore mike")
        # THEN
        self.assertListEqual(
            ["Stats: Joe will get 12.5 skill points for killing Mike"],
            self.joe.message_history,
        )

    def test_enemy(self):
        # GIVEN
        self.joe.team = TEAM_BLUE
        assert self.joe.team != self.mike.team
        # WHEN
        self.joe.says("!testscore mike")
        # THEN
        self.assertListEqual(
            ["Stats: Joe will get 12.5 skill points for killing Mike"],
            self.joe.message_history,
        )


class Test_cmd_topstats(StatPluginTestCase):
    def test_no_data(self):
        # WHEN
        self.joe.says("!topstats")
        # THEN
        self.assertListEqual(["Stats: No top players"], self.joe.message_history)

    def test_teammate(self):
        # GIVEN
        assert self.joe.team == self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topstats")
        # THEN
        self.assertListEqual(
            ["Top Stats: #1 Mike [100.0], #2 Joe [87.5]"], self.joe.message_history
        )

    def test_no_team(self):
        # GIVEN
        self.joe.team = TEAM_FREE
        self.mike.team = TEAM_FREE
        assert self.joe.team == self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topstats")
        # THEN
        self.assertListEqual(
            ["Top Stats: #1 Mike [100.0], #2 Joe [87.5]"], self.joe.message_history
        )

    def test_enemy(self):
        # GIVEN
        self.joe.team = TEAM_BLUE
        assert self.joe.team != self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topstats")
        # THEN
        self.assertListEqual(
            ["Top Stats: #1 Joe [112.5], #2 Mike [87.5]"], self.joe.message_history
        )


class Test_cmd_topxp(StatPluginTestCase):
    def test_no_data(self):
        # WHEN
        self.joe.says("!topxp")
        # THEN
        self.assertListEqual(
            ["Stats: No top experienced players"], self.joe.message_history
        )

    def test_teammate(self):
        # GIVEN
        assert self.joe.team == self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topxp")
        # THEN
        self.assertListEqual(
            ["Top Experienced Players: #1 Mike [0.0], #2 Joe [-0.0]"],
            self.joe.message_history,
        )

    def test_no_team(self):
        # GIVEN
        self.joe.team = TEAM_FREE
        self.mike.team = TEAM_FREE
        assert self.joe.team == self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topxp")
        # THEN
        self.assertListEqual(
            ["Top Experienced Players: #1 Mike [0.0], #2 Joe [-0.0]"],
            self.joe.message_history,
        )

    def test_enemy(self):
        # GIVEN
        self.joe.team = TEAM_BLUE
        assert self.joe.team != self.mike.team
        self.joe.kills(self.mike)
        # WHEN
        self.joe.says("!topxp")
        # THEN
        self.assertListEqual(
            ["Top Experienced Players: #1 Joe [12.5], #2 Mike [-0.0]"],
            self.joe.message_history,
        )
