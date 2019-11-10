import time

import unittest
from mock import Mock, patch
from mockito import when

from b3.config import XmlConfigParser
from b3.plugins.admin import AdminPlugin
from tests import logging_disabled


class CustomcommandsTestCase(unittest.TestCase):

    def setUp(self):
        self.sleep_patcher = patch("time.sleep")
        self.sleep_mock = self.sleep_patcher.start()

        # create a FakeConsole parser
        self.parser_conf = XmlConfigParser()
        self.parser_conf.loadFromString(r"""<configuration/>""")
        with logging_disabled():
            from b3.fake import FakeConsole
            self.console = FakeConsole(self.parser_conf)

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
            self.adminPlugin._commands = {}  # work around known bug in the Admin plugin which makes the _command property shared between all instances
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        self.console.screen = Mock()
        self.console.time = time.time
        self.console.upTime = Mock(return_value=3)

        self.console.cron.stop()

    def tearDown(self):
        self.sleep_patcher.stop()
