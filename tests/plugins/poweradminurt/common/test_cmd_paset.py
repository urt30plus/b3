import time
from unittest.mock import call, patch

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class mixin_cmd_paset:
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
paset: 20
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.sleep_patcher = patch.object(time, "sleep")
        self.sleep_patcher.start()
        self.setCvar_patcher = patch.object(self.console, "setCvar")
        self.setCvar_mock = self.setCvar_patcher.start()

        self.moderator.connects("2")

    def assert_setCvar_calls(self, expected_calls):
        self.assertListEqual(expected_calls, self.setCvar_mock.mock_calls)

    def tearDown(self):
        super().tearDown()
        self.sleep_patcher.stop()
        self.setCvar_patcher.stop()

    def test_nominal(self):
        # WHEN
        self.moderator.says("!paset sv_foo bar")
        # THEN
        self.assert_setCvar_calls([call("sv_foo", "bar")])
        self.assertListEqual([], self.moderator.message_history)

    def test_no_parameter(self):
        # WHEN
        self.moderator.says("!paset")
        # THEN
        self.assert_setCvar_calls([])
        self.assertListEqual(
            ["Invalid or missing data, try !help paset"], self.moderator.message_history
        )

    def test_no_value(self):
        # WHEN
        self.moderator.says("!paset sv_foo")
        # THEN
        self.assert_setCvar_calls([call("sv_foo", "")])
        self.assertListEqual([], self.moderator.message_history)


class Test_cmd_nuke_43(mixin_cmd_paset, Iourt43TestCase):
    """
    call the mixin test using the Iourt43TestCase parent class
    """
