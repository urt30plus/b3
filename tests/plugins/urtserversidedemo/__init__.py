# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2012 Thomas LEVEIL
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import logging
import unittest

from mock import Mock
from mockito.mockito import when

from b3.config import XmlConfigParser, CfgConfigParser
from b3.cvar import Cvar
from b3.parsers.iourt43 import Iourt43Parser
from b3.plugins.admin import AdminPlugin
from b3.plugins.urtserversidedemo import UrtserversidedemoPlugin


def write(*args, **kwargs):
    print("WRITE: %s" % args[0])
    return ""


class Iourt43_TestCase_mixin(unittest.TestCase):
    """
    Test case that makes Iourt43Parser inherits from FakeConsole
    """

    @classmethod
    def setUpClass(cls):
        # less logging
        logging.getLogger('output').setLevel(logging.ERROR)

        from b3.parsers.q3a.abstractParser import AbstractParser
        from b3.fake import FakeConsole
        AbstractParser.__bases__ = (FakeConsole,)
        # Now parser inheritance hierarchy is :
        # Iourt43Parser -> AbstractParser -> FakeConsole -> Parser


class Iourt43TestCase(Iourt43_TestCase_mixin):
    """
    Test case that is suitable for testing Iourt41 parser specific features
    """

    def setUp(self):
        # create a Iourt41 parser
        self.parser_conf = XmlConfigParser()
        self.parser_conf.loadFromString(
            """<configuration><settings name="server"><set name="game_log"></set></settings></configuration>""")
        self.console = Iourt43Parser(self.parser_conf)

        when(self.console).getCvar('gamename').thenReturn(Cvar('gamename', value='q3urt43'))
        when(self.console).getCvar('auth').thenReturn(None)
        when(self.console).getCvar('auth_owners').thenReturn(None)

        self.console.write = Mock(name="write", side_effect=write)
        self.console.startup()

        # load the admin plugin
        self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
        self.adminPlugin.onLoadConfig()
        self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        when(self.console).getPlugin("haxbusterurt").thenReturn(None)
        when(self.console).getPlugin("follow").thenReturn(None)

    def tearDown(self):
        self.console.working = False


class PluginTestCase(Iourt43TestCase):
    """
    Test case ready to test the UrtserversidedemoPlugin
    """
    CONF = ""

    def setUp(self):
        Iourt43TestCase.setUp(self)
        self.conf = CfgConfigParser()
        self.conf.loadFromString(self.__class__.CONF)
        self.p = UrtserversidedemoPlugin(self.console, self.conf)
        when(self.console).write('cmdlist startserverdemo').thenReturn("""\
startserverdemo
1 commands
""")
        logger = logging.getLogger('output')
        logger.setLevel(logging.NOTSET)
