import unittest
from mockito import when, unstub

from b3.config import CfgConfigParser
from b3.config import MainConfig
from b3.plugins.admin import AdminPlugin
from b3.plugins.duel import DuelPlugin
from tests import logging_disabled


class DuelTestCase(unittest.TestCase):

    def setUp(self):
        console_conf = CfgConfigParser()
        console_conf.loadFromString(r'''''')
        self.console_main_conf = MainConfig(console_conf)

        with logging_disabled():
            from b3.fake import FakeConsole
            self.console = FakeConsole(self.console_main_conf)

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
            self.adminPlugin._commands = {}
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        # create our plugin instance
        self.p = DuelPlugin(self.console)
        self.p.onStartup()

        with logging_disabled():
            from b3.fake import FakeClient

        self.mike = FakeClient(console=self.console, name="Mike", guid="MIKEGUID", groupBits=1)
        self.bill = FakeClient(console=self.console, name="Bill", guid="BILLGUID", groupBits=1)
        self.anna = FakeClient(console=self.console, name="Anna", guid="ANNAGUID", groupBits=1)

    def tearDown(self):
        unstub()
