from textwrap import dedent

from mockito import when, unstub

import b3
import b3.cron
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from b3.plugins.pluginmanager import PluginmanagerPlugin
from tests import B3TestCase


class PluginmanagerTestCase(B3TestCase):

    def setUp(self):
        B3TestCase.setUp(self)
        self.console.gameName = 'f00'

        self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
        when(self.console).getPlugin("admin").thenReturn(self.adminPlugin)
        when(self.console).getPlugin("fake").thenReturn(None)
        self.adminPlugin.onLoadConfig()
        self.adminPlugin.onStartup()

        self.conf = CfgConfigParser()
        self.conf.loadFromString(dedent(r"""
            [commands]
            plugin: superadmin
        """))

        self.p = PluginmanagerPlugin(self.console, self.conf)
        when(self.console).getPlugin("pluginmanager").thenReturn(self.adminPlugin)
        self.p.onLoadConfig()
        self.p.onStartup()

        when(self.console.config).get_external_plugins_dir().thenReturn(b3.functions.getAbsolutePath('@b3\\extplugins'))

        # store them also in the console _plugins dict
        self.console._plugins['admin'] = self.adminPlugin
        self.console._plugins['pluginmanager'] = self.p

    def tearDown(self):
        self.console._plugins.clear()
        B3TestCase.tearDown(self)
        unstub()
