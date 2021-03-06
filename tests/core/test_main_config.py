import configparser
import logging
import unittest
from textwrap import dedent

from b3.config import CfgConfigParser
from b3.config import MainConfig
from b3.config import XmlConfigParser
from b3.config import load
from b3.functions import getAbsolutePath


class CommonDefaultTestMethodsMixin:

    def test_b3_section(self):
        self.assertEqual('changeme', self.conf.get('b3', 'parser'))
        self.assertEqual('sqlite:///var/b3/b3_db.sqlite', self.conf.get('b3', 'database'))
        self.assertEqual('b3', self.conf.get('b3', 'bot_name'))
        self.assertEqual('^0(^2b3^0)^7:', self.conf.get('b3', 'bot_prefix'))
        self.assertEqual('%I:%M%p %Z %m/%d/%y', self.conf.get('b3', 'time_format'))
        self.assertEqual('LOCAL', self.conf.get('b3', 'time_zone'))
        self.assertEqual('9', self.conf.get('b3', 'log_level'))
        self.assertEqual('b3.log', self.conf.get('b3', 'logfile'))

    def test_server_section(self):
        self.assertEqual('password', self.conf.get('server', 'rcon_password'))
        self.assertEqual('27960', self.conf.get('server', 'port'))
        self.assertEqual('games_mp.log', self.conf.get('server', 'game_log'))
        self.assertEqual('127.0.0.1', self.conf.get('server', 'public_ip'))
        self.assertEqual('127.0.0.1', self.conf.get('server', 'rcon_ip'))
        self.assertEqual('0.33', self.conf.get('server', 'delay'))
        self.assertEqual('50', self.conf.get('server', 'lines_per_second'))

    def test_autodoc_section(self):
        self.assertEqual('html', self.conf.get('autodoc', 'type'))
        self.assertEqual('100', self.conf.get('autodoc', 'maxlevel'))
        with self.assertRaises(configparser.NoOptionError):
            self.conf.get('autodoc', 'destination')

    def test_update_section(self):
        self.assertEqual('stable', self.conf.get('update', 'channel'))

    def test_messages_section(self):
        self.assertEqual("""$clientname^7 was kicked by $adminname^7 $reason""", self.conf.get("messages", "kicked_by"))
        self.assertEqual("""$clientname^7 was kicked $reason""", self.conf.get("messages", "kicked"))
        self.assertEqual("""$clientname^7 was banned by $adminname^7 $reason""", self.conf.get("messages", "banned_by"))
        self.assertEqual("""$clientname^7 was banned $reason""", self.conf.get("messages", "banned"))
        self.assertEqual("""$clientname^7 was temp banned by $adminname^7 for $banduration^7 $reason""",
                         self.conf.get("messages", "temp_banned_by"))
        self.assertEqual("""$clientname^7 was temp banned for $banduration^7 $reason""",
                         self.conf.get("messages", "temp_banned"))
        self.assertEqual("""$clientname^7 was un-banned by $adminname^7 $reason""",
                         self.conf.get("messages", "unbanned_by"))
        self.assertEqual("""$clientname^7 was un-banned^7 $reason""", self.conf.get("messages", "unbanned"))

    def test_get_external_plugins_dir(self):
        self.assertEqual(getAbsolutePath("@b3/extplugins"), self.conf.get_external_plugins_dir())

    def test_get_plugins(self):
        self.assertListEqual([
            {'name': 'admin', 'conf': '@b3/conf/plugin_admin.ini', 'disabled': False, 'path': None},
            {'name': 'adv', 'conf': '@b3/conf/plugin_adv.xml', 'disabled': False, 'path': None},
            {'name': 'pluginmanager', 'conf': '@b3/conf/plugin_pluginmanager.ini', 'disabled': False, 'path': None},
            {'name': 'poweradminurt', 'conf': '@b3/conf/plugin_poweradminurt.ini', 'disabled': False, 'path': None},
            {'name': 'spree', 'conf': '@b3/conf/plugin_spree.ini', 'disabled': False, 'path': None},
            {'name': 'stats', 'conf': '@b3/conf/plugin_stats.ini', 'disabled': False, 'path': None},
            {'name': 'welcome', 'conf': '@b3/conf/plugin_welcome.ini', 'disabled': False, 'path': None},
            {'name': 'xlrstats', 'conf': '@b3/conf/plugin_xlrstats.ini', 'disabled': False, 'path': None},
        ], self.conf.get_plugins())


class Test_XmlMainConfigParser(CommonDefaultTestMethodsMixin, unittest.TestCase):

    def setUp(self):
        self.conf = MainConfig(load(getAbsolutePath('@b3/conf/b3.distribution.xml')))
        log = logging.getLogger('output')
        log.setLevel(logging.DEBUG)

    def test_plugins_order(self):
        """
        Vefify that the plugins are return in the same order as found in the config file
        """
        self.assertListEqual(
            ['admin', 'adv', 'pluginmanager', 'poweradminurt', 'spree', 'stats', 'welcome', 'xlrstats'],
            list([x.get('name') for x in self.conf._config_parser.get('plugins/plugin')]))


class Test_CfgMainConfigParser(CommonDefaultTestMethodsMixin, unittest.TestCase):

    def setUp(self):
        self.conf = MainConfig(load(getAbsolutePath('@b3/conf/b3.distribution.ini')))
        log = logging.getLogger('output')
        log.setLevel(logging.DEBUG)

    def test_plugins_order(self):
        """
        Vefify that the plugins are return in the same order as found in the config file
        """
        self.assertListEqual(
            ['admin', 'adv', 'pluginmanager', 'poweradminurt', 'spree', 'stats', 'welcome', 'xlrstats'], self.conf._config_parser.options('plugins'))


class TestConfig(unittest.TestCase):
    def init(self, xml_content, cfg_content):
        xml_parser = XmlConfigParser()
        xml_parser.loadFromString(xml_content)
        conf_xml = MainConfig(xml_parser)
        cfg_parser = CfgConfigParser(allow_no_value=True)
        cfg_parser.loadFromString(cfg_content)
        conf_cfg = MainConfig(cfg_parser)

        return conf_xml, conf_cfg

    def test_empty_conf(self):
        self.init(r"""<configuration/>""", "")

    def test_external_dir_missing(self):
        conf_xml, conf_cfg = self.init(dedent(r"""
            <configuration>
                <settings name="plugins">
                </settings>
            </configuration>
        """), dedent(r"""
            [b3]
        """))
        # normalized path for empty string is the current directory ('.')
        with self.assertRaises(configparser.NoOptionError):
            conf_xml.get_external_plugins_dir()
        with self.assertRaises(configparser.NoOptionError):
            conf_cfg.get_external_plugins_dir()

    def test_external_dir_empty(self):
        conf_xml, conf_cfg = self.init(dedent(r"""
            <configuration>
                <settings name="plugins">
                    <set name="external_dir" />
                </settings>
            </configuration>
        """), dedent(r"""
            [b3]
            external_plugins_dir:
        """))
        # normalized path for empty string is the current directory ('.')
        self.assertEqual(".", conf_xml.get_external_plugins_dir())
        self.assertEqual(".", conf_cfg.get_external_plugins_dir())

    def test_external_dir(self):
        conf_xml, conf_cfg = self.init(dedent(r"""
            <configuration>
                <settings name="plugins">
                    <set name="external_dir">f00</set>
                </settings>
            </configuration>
        """), dedent(r"""
            [b3]
            external_plugins_dir: f00
        """))
        # normalized path for empty string is the current directory ('.')
        self.assertEqual("f00", conf_xml.get_external_plugins_dir())
        self.assertEqual("f00", conf_cfg.get_external_plugins_dir())

    def test_plugins_missing(self):
        conf_xml, conf_cfg = self.init(dedent(r"""
            <configuration>
                <plugins />
            </configuration>
        """), dedent(r"""
            [plugins]
        """))
        # normalized path for empty string is the current directory ('.')
        self.assertListEqual([], conf_xml.get_plugins())
        self.assertListEqual([], conf_cfg.get_plugins())

    def test_plugins(self):
        conf_xml, conf_cfg = self.init(dedent(r"""
            <configuration>
                <plugins>
                    <plugin name="admin" config="@b3/conf/plugin_admin.ini" />
                    <plugin name="adv" config="@b3/conf/plugin_adv.xml" disabled="yes" />
                    <plugin name="censor" config="@b3/conf/plugin_censor.xml" disabled="no" />
                    <plugin name="cmdmanager" config="@b3/conf/plugin_cmdmanager.ini" path="/somewhere/else" />
                    <plugin name="tk" config="@b3/conf/plugin_tk.ini" disabled="1" />
                </plugins>
            </configuration>
        """), dedent(r"""
            [b3]
            disabled_plugins: adv, tk

            [plugins]
            admin: @b3/conf/plugin_admin.ini
            adv: @b3/conf/plugin_adv.xml
            censor: @b3/conf/plugin_censor.xml
            cmdmanager: @b3/conf/plugin_cmdmanager.ini
            tk: @b3/conf/plugin_tk.ini

            [plugins_custom_path]
            cmdmanager: /somewhere/else
        """))
        # normalized path for empty string is the current directory ('.')
        expected_result = [
            {'name': 'admin', 'conf': '@b3/conf/plugin_admin.ini', 'disabled': False, 'path': None},
            {'name': 'adv', 'conf': '@b3/conf/plugin_adv.xml', 'disabled': True, 'path': None},
            {'name': 'censor', 'conf': '@b3/conf/plugin_censor.xml', 'disabled': False, 'path': None},
            {'name': 'cmdmanager', 'conf': '@b3/conf/plugin_cmdmanager.ini', 'disabled': False,
             'path': '/somewhere/else'},
            {'name': 'tk', 'conf': '@b3/conf/plugin_tk.ini', 'disabled': True, 'path': None},
        ]
        self.assertListEqual(expected_result, conf_xml.get_plugins())
        self.assertListEqual(expected_result, conf_cfg.get_plugins())
