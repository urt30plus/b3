import time
from unittest.mock import Mock, patch

from mockito import verify, when

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class mixin_cmd_pasetnextmap:
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString(
            """
[commands]
pasetnextmap-snmap: 20
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

    def test_missing_parameter(self):
        self.moderator.clearMessageHistory()
        self.moderator.says("!snmap")
        self.assertEqual(
            ["Invalid or missing data, try !help pasetnextmap"],
            self.moderator.message_history,
        )

    def test_existing_map(self):
        # GIVEN
        when(self.console).getMapsSoundingLike("f00").thenReturn("f00")
        # WHEN
        self.moderator.clearMessageHistory()
        self.moderator.says("!snmap f00")
        # THEN
        verify(self.console).getMapsSoundingLike("f00")
        self.assertEqual(["nextmap set to f00"], self.moderator.message_history)

    def test_suggestions(self):
        # GIVEN
        when(self.console).getMapsSoundingLike("f00").thenReturn(["f001", "foo2"])
        # WHEN
        self.moderator.clearMessageHistory()
        self.moderator.says("!snmap f00")
        # THEN
        verify(self.console).getMapsSoundingLike("f00")
        self.assertEqual(["do you mean : f001, foo2 ?"], self.moderator.message_history)


class Test_cmd_nuke_43(mixin_cmd_pasetnextmap, Iourt43TestCase):
    """
    call the mixin test using the Iourt43TestCase parent class
    """
