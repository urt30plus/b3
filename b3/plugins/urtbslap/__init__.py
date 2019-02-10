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

__author__ = 'HSO Clan Development http://www.hsoclan.co.uk'
__version__ = '0.0.2'

import b3.plugin


class UrtbslapPlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._admin_plugin = None
        self._slap_safe_level = 100

    def onLoadConfig(self):
        self._slap_safe_level = self.getSetting("settings", "slap_safe_level", b3.INTEGER, default=100)

    def onStartup(self):
        self.register_commands_from_config()
        self._admin_plugin = self.console.getPlugin('admin')

    def cmd_mslap(self, data, client=None, cmd=None):
        """
        <name> <number of slaps> - slap a player multiple times
        """
        input = self._admin_plugin.parseUserCmd(data)
        if not input:
            client.message('^7command is !mslap <playername or partialname> <number of slaps>')
            return False
        if len(input) < 2 or not input[1] or not input[1].isdigit():
            client.message('^7 correct syntax is !mslap <playername or part> <number of slaps>')
            return False
        cname = input[0]
        creps = input[1]
        sclient = self._admin_plugin.findClientPrompt(cname, client)
        if not sclient:
            return False
        if sclient.maxLevel >= self._slap_safe_level:
            client.message("^7You don't have enough privileges to slap this Admin")
            return False
        self.console.write('bigtext "^7Play by 30+ Rules Please!"')
        self.__do_slap(sclient, int(creps))
        return True

    def cmd_bslap(self, data, client=None, cmd=None):
        """
        <name> - slap a player to death
        """
        input = self._admin_plugin.parseUserCmd(data)
        if not input:
            client.message('^7Slap who???')
            return False
        sclient = self._admin_plugin.findClientPrompt(input[0], client)
        if not sclient:
            return False
        if sclient.maxLevel >= self._slap_safe_level:
            client.message("^7You don't have enough privileges to slap this Admin")
            return False
        self.console.write('bigtext "^7Slapped to Death Because You Deserved It!"')
        self.__do_slap(sclient, 20)
        return True

    def __do_slap(self, sclient, reps):
        while reps > 0:
            self.console.write(f'slap {sclient.cid}')
            reps -= 1
