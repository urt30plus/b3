import logging
from unittest.mock import patch

from mockito import unstub

from b3.config import CfgConfigParser
from b3.plugins.spamcontrol import SpamcontrolPlugin
from tests import B3TestCase


class SpamcontrolTestCase(B3TestCase):
    """
    Ease testcases that need an working B3 console and need to control the Spamcontrol plugin config
    """

    def setUp(self):
        self.timer_patcher = patch("threading.Timer")
        self.timer_patcher.start()

        self.log = logging.getLogger("output")
        self.log.propagate = False

        B3TestCase.setUp(self)
        self.console.startup()
        self.log.propagate = True

    def tearDown(self):
        B3TestCase.tearDown(self)
        self.timer_patcher.stop()
        unstub()

    def init_plugin(self, config_content):
        self.conf = CfgConfigParser()
        self.conf.loadFromString(config_content)
        self.p = SpamcontrolPlugin(self.console, self.conf)

        self.log.setLevel(logging.DEBUG)
        self.log.info(
            "============================= Spamcontrol plugin: loading config ============================"
        )
        self.p.onLoadConfig()
        self.log.info(
            "============================= Spamcontrol plugin: starting  ================================="
        )
        self.p.onStartup()
