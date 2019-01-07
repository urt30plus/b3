# -*- coding: utf-8 -*-

# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #

import os

import pytest
from mockito import when

from b3 import TEAM_UNKNOWN
from b3.config import CfgConfigParser
from b3.plugins.admin import AdminPlugin
from b3.plugins.afk import AfkPlugin
from tests import logging_disabled

DEFAULT_PLUGIN_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../../b3/conf/plugin_afk.ini')


@pytest.fixture
def console():
    with logging_disabled():
        from b3.fake import FakeConsole
        fake_console = FakeConsole('@b3/conf/b3.distribution.xml')
        admin_plugin_conf_file = '@b3/conf/plugin_admin.ini'
        admin_plugin = AdminPlugin(fake_console, admin_plugin_conf_file)
        admin_plugin._commands = {}  # work around known bug in the Admin plugin which makes the _command property shared between all instances
        admin_plugin.onStartup()

    # make sure the admin plugin obtained by other plugins is our admin plugin
    when(fake_console).getPlugin('admin').thenReturn(admin_plugin)

    return fake_console


def plugin_maker(console_obj, conf):
    p = AfkPlugin(console_obj, conf)
    return p


def plugin_maker_ini(console_obj, conf_content):
    conf = CfgConfigParser()
    conf.loadFromString(conf_content)
    return plugin_maker(console_obj, conf)


@pytest.fixture
def superadmin(console):
    with logging_disabled():
        from b3.fake import FakeClient
    client = FakeClient(console, name="Superadmin", guid="superadmin_guid", groupBits=128, team=TEAM_UNKNOWN)
    client.clearMessageHistory()
    return client


@pytest.fixture
def joe(console):
    with logging_disabled():
        from b3.fake import FakeClient
    client = FakeClient(console, name="Joe", guid="joe_guid", groupBits=1, team=TEAM_UNKNOWN)
    client.clearMessageHistory()
    return client


@pytest.fixture
def jack(console):
    with logging_disabled():
        from b3.fake import FakeClient
    client = FakeClient(console, name="Jack", guid="jack_guid", groupBits=1, team=TEAM_UNKNOWN)
    client.clearMessageHistory()
    return client


@pytest.fixture
def bot(console):
    with logging_disabled():
        from b3.fake import FakeClient
    client = FakeClient(console, name="Bot", guid="bot_guid", groupBits=1, team=TEAM_UNKNOWN, bot=True)
    client.clearMessageHistory()
    return client
