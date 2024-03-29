import time
from unittest.mock import Mock, patch

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from b3.plugins.poweradminurt import (
    __author__ as plugin_author,
)
from b3.plugins.poweradminurt import (
    __version__ as plugin_version,
)
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class mixin_cmd_version:
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
paversion-version: 20
        """
        )
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.sleep_patcher = patch.object(time, "sleep")
        self.sleep_patcher.start()

        self.console.say = Mock()
        self.console.saybig = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def tearDown(self):
        super().tearDown()
        self.sleep_patcher.stop()

    def test_nominal(self):
        self.moderator.message_history = []
        self.moderator.says("!version")
        self.assertEqual(
            [f"I am PowerAdminUrt version {plugin_version} by {plugin_author}"],
            self.moderator.message_history,
        )


class Test_cmd_nuke_43(mixin_cmd_version, Iourt43TestCase):
    """
    call the mixin_cmd_nuke test using the Iourt43TestCase parent class
    """
