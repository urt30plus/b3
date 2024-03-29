import b3
from b3 import TEAM_BLUE, TEAM_RED
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from tests import B3TestCase
from tests.fake import FakeClient


class Admin_TestCase(B3TestCase):
    """
    Tests from a class inherithing from Admin_TestCase must call self.init().
    """

    def setUp(self):
        B3TestCase.setUp(self)
        self.conf = CfgConfigParser()
        self.p = AdminPlugin(self.console, self.conf)

    def init(self, config_content=None):
        """
        Optionally specify a config for the plugin. If called with no parameter, then the default config is loaded.
        """
        if config_content is None:
            self.conf.load(b3.functions.getAbsolutePath("@b3/conf/plugin_admin.ini"))
        else:
            self.conf.loadFromString(config_content)
        self.p.onLoadConfig()
        self.p.onStartup()


class Admin_functional_test(B3TestCase):
    """tests from a class inheriting from Admin_functional_test must call self.init()"""

    def setUp(self):
        B3TestCase.setUp(self)
        self.conf = CfgConfigParser()
        self.p = AdminPlugin(self.console, self.conf)

    def init(self, config_content=None):
        """optionally specify a config for the plugin. If called with no parameter, then the default config is loaded"""
        if config_content is None:
            self.conf.load(b3.functions.getAbsolutePath("@b3/conf/plugin_admin.ini"))
        else:
            self.conf.loadFromString(config_content)

        self.p._commands = {}
        self.p.onLoadConfig()
        self.p.onStartup()

        self.joe = FakeClient(
            self.console,
            name="Joe",
            exactName="Joe",
            guid="joeguid",
            groupBits=128,
            team=TEAM_RED,
        )
        self.mike = FakeClient(
            self.console,
            name="Mike",
            exactName="Mike",
            guid="mikeguid",
            groupBits=1,
            team=TEAM_BLUE,
        )
