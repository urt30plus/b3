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

from tests.plugins.adv import AdvTestCase


class Test_config(AdvTestCase):

    def test_default_config(self):
        self.init_plugin()
        self.assertEqual('3', self.p._rate)
        self.assertIsNone(self.p._fileName)
        self.assertIsNotNone(self.p._cronTab)
        self.assertTupleEqual((0, list(range(0, 59, 3)), -1, -1, -1, -1),
                              (self.p._cronTab.second, self.p._cronTab.minute, self.p._cronTab.hour,
                               self.p._cronTab.day, self.p._cronTab.month, self.p._cronTab.dow))
        self.assertEqual(12, len(self.p._msg.items))
        self.assertListEqual([
            '^2Yes, we are watching.',
            '^2Visit us at www.urt-30plus.org.',
            '^2Public Teamspeak 3 server: ts3.urt-30plus.org.',
            '^2Type !register to register as a user.',
            '^2Type !fa in chat to forgive team damage!',
            '^2Send demos to admin@urt-30plus.org',
            '^3Rule #8: No profanity or offensive language (in any language)',
            '@time',
            '@nextmap',
            '^2Type !help for commands.',
            '^2Type !xlrstats for statistics.',
            '@topstats'
        ], self.p._msg.items)

    def test_empty(self):
        self.init_plugin("""<configuration plugin="adv" />""")
        self.assertEqual(self.p._rate, '2')
        self.assertIsNone(self.p._fileName)
        self.assertEqual(0, len(self.p._msg.items))
        self.assertIsNotNone(self.p._cronTab)

    def test_rate_nominal(self):
        self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">1</set>
    </settings>
</configuration>
""")
        self.assertEqual('1', self.p._rate)
        self.assertIsNotNone(self.p._cronTab)
        self.assertTupleEqual((0, list(range(60)), -1, -1, -1, -1),
                              (self.p._cronTab.second, self.p._cronTab.minute, self.p._cronTab.hour,
                               self.p._cronTab.day, self.p._cronTab.month, self.p._cronTab.dow))

    def test_rate_nominal_second(self):
        self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">40s</set>
    </settings>
</configuration>
""")
        self.assertEqual('40s', self.p._rate)
        self.assertIsNotNone(self.p._cronTab)
        self.assertTupleEqual(([0, 40], -1, -1, -1, -1, -1),
                              (self.p._cronTab.second, self.p._cronTab.minute, self.p._cronTab.hour,
                               self.p._cronTab.day, self.p._cronTab.month, self.p._cronTab.dow))

    def test_rate_junk(self):
        try:
            self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">f00</set>
    </settings>
</configuration>
""")
        except TypeError as err:
            print(err)
        except Exception:
            raise
        self.assertEqual('f00', self.p._rate)
        self.assertIsNone(self.p._cronTab)
