from textwrap import dedent

from mock import patch

from b3.config import CfgConfigParser
from b3.plugins.status import StatusPlugin
from tests import B3TestCase


class Test_config(B3TestCase):

    @patch("b3.cron.PluginCronTab")
    def test_no_svar_table(self, pluginCronTab_mock):
        conf = CfgConfigParser()
        conf.loadFromString(dedent(r"""
            [settings]
            interval: 60
            output_file: ~/status.xml
            enableDBsvarSaving: no
            enableDBclientSaving: no
            """))
        self.p = StatusPlugin(self.console, conf)
        self.p._tables = {'svars': 'current_svars', 'cvars': 'current_clients'}
        self.p.onLoadConfig()
        self.assertEqual("current_svars", self.p._tables['svars'])

    @patch("b3.cron.PluginCronTab")
    def test_svar_table(self, pluginCronTab_mock):
        conf = CfgConfigParser()
        conf.loadFromString(dedent(r"""
            [settings]
            interval: 60
            output_file: ~/status.xml
            enableDBsvarSaving: yes
            enableDBclientSaving: no
            svar_table: alternate_svar_table
            """))
        self.p = StatusPlugin(self.console, conf)
        self.p._tables = {'svars': 'current_svars', 'cvars': 'current_clients'}
        self.p.onLoadConfig()
        self.assertEqual("alternate_svar_table", self.p._tables['svars'])

    @patch("b3.cron.PluginCronTab")
    def test_no_client_table(self, pluginCronTab_mock):
        conf = CfgConfigParser()
        conf.loadFromString(dedent(r"""
            [settings]
            interval: 60
            output_file: ~/status.xml
            enableDBsvarSaving: no
            enableDBclientSaving: no
            """))
        self.p = StatusPlugin(self.console, conf)
        self.p._tables = {'svars': 'current_svars', 'cvars': 'current_clients'}
        self.p.onLoadConfig()
        self.assertEqual("current_clients", self.p._tables['cvars'])

    @patch("b3.cron.PluginCronTab")
    def test_client_table(self, pluginCronTab_mock):
        conf = CfgConfigParser()
        conf.loadFromString(dedent(r"""
            [settings]
            interval: 60
            output_file: ~/status.xml
            enableDBsvarSaving: no
            enableDBclientSaving: yes
            client_table: alternate_client_table
            """))
        self.p = StatusPlugin(self.console, conf)
        self.p._tables = {'svars': 'current_svars', 'cvars': 'current_clients'}
        self.p.onLoadConfig()
        self.assertEqual("alternate_client_table", self.p._tables['cvars'])
