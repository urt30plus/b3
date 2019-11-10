import unittest
from textwrap import dedent

from mockito import when, unstub

from b3.config import CfgConfigParser
from b3.config import MainConfig
from b3.plugins.admin import AdminPlugin
from b3.plugins.spree import SpreePlugin
from tests import logging_disabled


class SpreeTestCase(unittest.TestCase):

    def setUp(self):
        # create a FakeConsole parser
        parser_ini_conf = CfgConfigParser()
        parser_ini_conf.loadFromString(r'''''')
        self.parser_main_conf = MainConfig(parser_ini_conf)

        with logging_disabled():
            from b3.fake import FakeConsole
            self.console = FakeConsole(self.parser_main_conf)

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
            self.adminPlugin._commands = {}
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        # create our plugin instance
        self.p = SpreePlugin(self.console, CfgConfigParser())

        with logging_disabled():
            from b3.fake import FakeClient

        self.mike = FakeClient(console=self.console, name="Mike", guid="MIKEGUID", groupBits=1)
        self.bill = FakeClient(console=self.console, name="Bill", guid="BILLGUID", groupBits=1)

    def tearDown(self):
        unstub()

    def init(self, config_content=None):
        """
        Initialize the plugin using the given configuration file content
        """
        if not config_content:
            config_content = dedent(r"""
                [settings]
                reset_spree: yes

                [killingspree_messages]
                5: %player% is on a killing spree (5 kills in a row) # %player% stopped the spree of %victim%
                10: %player% is on fire! (10 kills in a row) # %player% iced %victim%

                [loosingspree_messages]
                12: Keep it up %player%, it will come eventually # You're back in business %player%

                [commands]
                spree: user
            """)

        self.p.config.loadFromString(config_content)
        self.p.onLoadConfig()
        self.p.onStartup()
