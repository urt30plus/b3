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
    minlevel = 0
    _slap_safe_level = 0
    _adminPlugin = None

    def onLoadConfig(self):
        try:
            self.minlevel = self.config.getint('settings', 'minlevel')
        except:
            self.minlevel = 80
        self.debug(f"minlevel set to {self.minlevel}")

        try:
            self._slap_safe_level = self.config.getint('settings', 'slap_safe_level')
        except:
            self._slap_safe_level = 100
        self.debug(f"slap safe level set to {self._slap_safe_level}")

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if self._adminPlugin:
            self._adminPlugin.registerCommand(self, 'mslap', self.minlevel, self.cmd_mslap, 'f')
            self._adminPlugin.registerCommand(self, 'bslap', self.minlevel, self.cmd_bslap, 'f')

    def cmd_mslap(self, data, client=None, cmd=None):
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7command is !mslap <playername or partialname> <number of slaps>')
            return False
        if len(input) < 2 or not input[1] or not input[1].isdigit():
            client.message('^7 correct syntax is !mslap <playername or part> <number of slaps>')
            return False
        cname = input[0]
        creps = input[1]
        sclient = self._adminPlugin.findClientPrompt(cname, client)
        if not sclient:
            return False
        if sclient.maxLevel >= self._slap_safe_level:
            client.message("^7You don't have enough privileges to slap this Admin")
            return False
        self.console.write('bigtext "^7Play by 30+ Rules Please!"')
        self.__do_slap(sclient, int(creps))
        return True

    def cmd_bslap(self, data, client=None, cmd=None):
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7Slap who???')
            return False
        sclient = self._adminPlugin.findClientPrompt(input[0], client)
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
            self.console.write('slap %s' % (sclient.cid))
            reps -= 1
