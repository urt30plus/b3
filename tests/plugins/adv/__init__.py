import logging
import os
import unittest
from unittest.mock import Mock, patch

from mockito import unstub, when

from b3 import __file__ as b3_module__file__
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from b3.plugins.adv import AdvPlugin
from tests import B3TestCase

ADMIN_CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(b3_module__file__), "conf/plugin_admin.ini")
)
ADV_CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../../b3/conf/plugin_adv.ini")
)
ADV_CONFIG_CONTENT = None

timer_patcher = None


class AdvTestCase(B3TestCase):
    """
    Ease test cases that need an working B3 console and need to control the ADV plugin config
    """

    def setUp(self):
        self.log = logging.getLogger("output")
        self.log.propagate = False

        B3TestCase.setUp(self)

        global ADV_CONFIG_CONTENT, ADV_CONFIG_FILE, ADMIN_CONFIG_FILE, timer_patcher
        if os.path.exists(ADV_CONFIG_FILE):
            with open(ADV_CONFIG_FILE) as f:
                ADV_CONFIG_CONTENT = f.read()

        self.adminPluginConf = CfgConfigParser()
        self.adminPluginConf.load(ADMIN_CONFIG_FILE)
        self.adminPlugin = AdminPlugin(self.console, self.adminPluginConf)
        when(self.console).getPlugin("admin").thenReturn(self.adminPlugin)

        self.adminPlugin.onLoadConfig()
        self.adminPlugin.onStartup()

        self.console.startup()
        self.log.propagate = True

        timer_patcher = patch("threading.Timer")
        timer_patcher.start()

    def tearDown(self):
        B3TestCase.tearDown(self)
        timer_patcher.stop()
        unstub()

    def init_plugin(self, config_content=None):
        conf = None
        if config_content:
            conf = CfgConfigParser()
            conf.loadFromString(config_content)
        elif ADV_CONFIG_CONTENT:
            conf = CfgConfigParser()
            conf.loadFromString(ADV_CONFIG_CONTENT)
        else:
            unittest.skip(
                "cannot get default plugin config file at %s" % ADV_CONFIG_FILE
            )

        self.p = AdvPlugin(self.console, conf)
        self.p.save = Mock()
        self.conf = self.p.config
        self.log.setLevel(logging.DEBUG)
        self.log.info(
            "============================= Adv plugin: loading config ============================"
        )
        self.p.onLoadConfig()
        self.log.info(
            "============================= Adv plugin: starting  ================================="
        )
        self.p.onStartup()
