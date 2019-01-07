# -*- encoding: utf-8 -*-
# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Courgette
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
#
from mock import call, Mock

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_cmd_gungame(Iourt43TestCase):

    def setUp(self):
        super(Test_cmd_gungame, self).setUp()
        self.conf = CfgConfigParser()
        self.conf.loadFromString("""
[commands]
pagungame-gungame: 20           ; change game type to Gun Game
        """)
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        self.p.onLoadConfig()
        self.p.onStartup()

        self.console.say = Mock()
        self.console.write = Mock()

        self.moderator.connects("2")

    def test_nominal(self):
        self.moderator.message_history = []
        self.moderator.says("!gungame")
        self.console.write.assert_has_calls([call('set g_gametype "11"')])
        self.assertEqual(['game type changed to Gun Game'], self.moderator.message_history)
